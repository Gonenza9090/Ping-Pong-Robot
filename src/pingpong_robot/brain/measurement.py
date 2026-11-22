"""Repeated segmentation on a frozen frame; robust statistics, not accuracy claims."""

from dataclasses import dataclass
import random
from statistics import median
import cv2
import numpy as np
from .geometry import distance_cm, resolve_height


def _strongest(gradient, center, margin):
    lower, upper = max(0, center - margin), min(len(gradient), center + margin + 1)
    if lower >= upper:
        return center
    window = gradient[lower:upper]
    strongest = window.max()
    if strongest <= 0:
        return center  # A flat image provides no evidence for moving an edge.
    candidates = np.flatnonzero(window == strongest) + lower
    return int(candidates[np.argmin(np.abs(candidates - center))])


def refined_edges(frame, bbox, margin=15, samples=7):
    """Median-vote gradient edges near the segmentation; never search outside the image."""
    x, y, w, h = bbox
    image_h, image_w = frame.shape[:2]
    if min(w, h) < 2 or margin == 0:
        return x, y, x + w, y + h
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    xs = np.unique(np.clip(np.linspace(x + .2 * (w - 1), x + .8 * (w - 1), samples).astype(int), 0, image_w - 1))
    ys = np.unique(np.clip(np.linspace(y + .2 * (h - 1), y + .8 * (h - 1), samples).astype(int), 0, image_h - 1))
    tops, bottoms, lefts, rights = [], [], [], []
    for col in xs:
        gradient = np.abs(np.gradient(gray[:, col]))
        tops.append(_strongest(gradient, y, margin))
        bottoms.append(_strongest(gradient, y + h - 1, margin) + 1)
    for row in ys:
        gradient = np.abs(np.gradient(gray[row, :]))
        lefts.append(_strongest(gradient, x, margin))
        rights.append(_strongest(gradient, x + w - 1, margin) + 1)
    bounds = (int(median(lefts)), int(median(tops)), int(median(rights)), int(median(bottoms)))
    x1, y1, x2, y2 = bounds
    if not (0 <= x1 < x2 <= image_w and 0 <= y1 < y2 <= image_h):
        return x, y, x + w, y + h
    return bounds


@dataclass(frozen=True)
class Measurement:
    bbox: tuple[int, int, int, int]  # raw x1, y1, x2, y2
    centroid: tuple[int, int]
    raw_height_px: float
    raw_width_px: float
    used_height_px: float
    distance_cm: float | None
    samples_used: int
    height_spread_px: float
    method: str
    ratio_disagreement_pct: float | None


def measure(frame, point, roi, segmenter, config, calibration=None, obj=None, rng=None):
    if calibration is not None:
        calibration.check_frame(frame.shape)
    rng = rng if rng is not None else random.Random()
    h, w = frame.shape[:2]
    if not (0 <= roi[0] < roi[2] <= w and 0 <= roi[1] < roi[3] <= h):
        raise ValueError("Selection box must be inside the raw image")
    if not (roi[0] <= point[0] < roi[2] and roi[1] <= point[1] < roi[3]):
        raise ValueError("Click must be inside the selection box")
    rows = []
    first_segment = None
    for index in range(config.samples):
        dx = 0 if index == 0 else rng.randint(-config.jitter_px, config.jitter_px)
        dy = 0 if index == 0 else rng.randint(-config.jitter_px, config.jitter_px)
        x = min(max(point[0] + dx, roi[0]), roi[2] - 1)
        y = min(max(point[1] + dy, roi[1]), roi[3] - 1)
        segment = segmenter.segment(frame, (x, y), roi)
        if segment is None:
            continue
        if first_segment is not None:
            intersection = np.count_nonzero((segment.mask > 0) & (first_segment.mask > 0))
            union = np.count_nonzero((segment.mask > 0) | (first_segment.mask > 0))
            if union == 0 or intersection / union < .5:
                continue  # Jitter moved onto another object: do not mix its dimensions.
        else:
            first_segment = segment
        x1, y1, x2, y2 = refined_edges(frame, segment.bbox, config.edge_margin_px)
        if x2 > x1 and y2 > y1:
            rows.append((x1, y1, x2, y2))
    if not rows:
        raise ValueError("No valid foreground at the click; change the point or box and retry")
    bounds = tuple(int(median(r[i] for r in rows)) for i in range(4))
    x1, y1, x2, y2 = bounds
    raw_height, raw_width = y2 - y1, x2 - x1
    heights = [r[3] - r[1] for r in rows]
    selected = None if obj is None else resolve_height(
        raw_height, raw_width, obj, use_width=config.width_correction,
        tolerance_pct=config.ratio_tolerance_pct,
    )
    used = raw_height if selected is None else selected.height_px
    distance = None if calibration is None or obj is None else distance_cm(obj.height_cm, calibration.focal_length_px, used)
    return Measurement(
        bounds, ((x1 + x2) // 2, (y1 + y2) // 2), raw_height, raw_width, used,
        distance, len(rows), max(heights) - min(heights),
        "pixels_only" if selected is None else selected.method,
        None if selected is None else selected.ratio_disagreement_pct,
    )
