"""Display-only zoom: all segmentation and measurement use original pixels."""

from dataclasses import dataclass
import cv2


@dataclass(frozen=True)
class Viewport:
    x0: int
    y0: int
    crop_width: int
    crop_height: int
    display_width: int
    display_height: int

    def to_raw(self, x, y):
        x = max(0, min(self.display_width - 1, x))
        y = max(0, min(self.display_height - 1, y))
        return (
            self.x0 + min(self.crop_width - 1, int(x * self.crop_width / self.display_width)),
            self.y0 + min(self.crop_height - 1, int(y * self.crop_height / self.display_height)),
        )

    def to_display(self, x, y):
        return (round((x - self.x0) * self.display_width / self.crop_width),
                round((y - self.y0) * self.display_height / self.crop_height))


def render_view(frame, zoom=1.0, max_width=1280, max_height=720):
    if zoom < 1 or zoom > 3:
        raise ValueError("Display zoom must be between 1 and 3")
    h, w = frame.shape[:2]
    crop_w, crop_h = max(1, round(w / zoom)), max(1, round(h / zoom))
    x0, y0 = (w - crop_w) // 2, (h - crop_h) // 2
    scale = min(max_width / w, max_height / h, 1.0)
    display_w, display_h = max(1, round(w * scale)), max(1, round(h * scale))
    view = Viewport(x0, y0, crop_w, crop_h, display_w, display_h)
    image = cv2.resize(frame[y0:y0 + crop_h, x0:x0 + crop_w], (display_w, display_h))
    return image, view
