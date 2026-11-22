"""Pure measurement math, separated from cameras and GUI state."""

from dataclasses import dataclass
import math
from ..config import KnownObject, positive


def focal_length_px(real_height_cm, distance_cm, pixel_height):
    return positive(pixel_height, "pixel_height") * positive(distance_cm, "distance_cm") / positive(real_height_cm, "real_height_cm")


def distance_cm(real_height_cm, focal_px, pixel_height):
    return positive(real_height_cm, "real_height_cm") * positive(focal_px, "focal_px") / positive(pixel_height, "pixel_height")


@dataclass(frozen=True)
class HeightChoice:
    height_px: float
    method: str
    ratio_disagreement_pct: float | None = None


def resolve_height(height_px, width_px, obj: KnownObject, *, use_width=False, tolerance_pct=20):
    """Keep the original aspect-ratio idea, but opt in only with measured widths.

    This is an experimental heuristic, not a segmentation-quality guarantee.
    Both estimates come from the same frozen frame and are correlated.
    """
    height = positive(height_px, "height_px")
    width = positive(width_px, "width_px")
    if not use_width or not obj.width_verified or obj.width_cm is None:
        return HeightChoice(height, "height_only")
    derived = obj.height_cm * width / positive(obj.width_cm, "width_cm")
    disagreement = abs(height - derived) / derived * 100
    if disagreement <= positive(tolerance_pct, "tolerance_pct"):
        return HeightChoice((height + derived) / 2, "height_width_average", disagreement)
    return HeightChoice(derived, "experimental_width_fallback", disagreement)
