"""GrabCut and optional MobileSAM share one prompt and mask contract."""

from dataclasses import dataclass
import cv2
import numpy as np


@dataclass(frozen=True)
class Segment:
    mask: np.ndarray
    contour: np.ndarray
    centroid: tuple[int, int]
    bbox: tuple[int, int, int, int]


def clamp_box(point, half_width, half_height, frame_shape):
    h, w = frame_shape[:2]
    x, y = point
    # Upper bounds are exclusive, matching NumPy slicing/OpenCV rectangles.
    return (max(0, x - half_width), max(0, y - half_height),
            min(w, x + half_width + 1), min(h, y + half_height + 1))


def clicked_component(mask, point):
    binary = (mask > 0).astype(np.uint8)
    h, w = binary.shape
    x, y = point
    if not (0 <= x < w and 0 <= y < h) or not binary[y, x]:
        return None
    _, labels = cv2.connectedComponents(binary, connectivity=8)
    selected = (labels == labels[y, x]).astype(np.uint8)
    contours, _ = cv2.findContours(selected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    m = cv2.moments(contour)
    if m["m00"] <= 0:
        return None
    centroid = (round(m["m10"] / m["m00"]), round(m["m01"] / m["m00"]))
    return Segment(selected, contour, centroid, cv2.boundingRect(contour))


class GrabCutSegmenter:
    name = "grabcut"

    def segment(self, frame, point, roi):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = roi
        if x2 - x1 < 2 or y2 - y1 < 2:
            return None
        mask = np.zeros((h, w), dtype=np.uint8)
        if x1 == 0 and y1 == 0 and x2 == w and y2 == h:
            # GrabCut needs at least some background outside its initial rectangle.
            return None
        try:
            cv2.grabCut(frame, mask, (x1, y1, x2 - x1, y2 - y1),
                        np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64),
                        5, cv2.GC_INIT_WITH_RECT)
        except cv2.error:
            return None
        foreground = np.isin(mask, [cv2.GC_FGD, cv2.GC_PR_FGD])
        return clicked_component(foreground, point)


class SamSegmenter:
    name = "sam"

    def __init__(self, weights):
        # Import/load only when explicitly selected, never at module import time.
        try:
            import torch
            from ultralytics import SAM
        except ImportError as error:
            raise RuntimeError('Install optional SAM support: python -m pip install -e ".[sam]"') from error
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SAM(weights)

    def segment(self, frame, point, roi):
        results = self.model.predict(
            frame, points=[list(point)], labels=[1], bboxes=[list(roi)],
            device=self.device, verbose=False,
        )
        if not results or results[0].masks is None:
            return None
        # Select the component at the actual clicked point, not the largest other object.
        for raw_mask in results[0].masks.data:
            mask = raw_mask.detach().cpu().numpy()
            mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
            selected = clicked_component(mask > 0.5, point)
            if selected is not None:
                return selected
        return None


def make_segmenter(backend, weights="models/mobile_sam.pt"):
    if backend == "grabcut":
        return GrabCutSegmenter()
    if backend == "sam":
        return SamSegmenter(weights)
    raise ValueError("backend must be grabcut or sam")
