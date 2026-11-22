"""Validated local configuration. Camera credentials never belong in Git."""

from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import tomllib
from urllib.parse import urlsplit


def positive(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, not a boolean")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return number


def pixel_count(value, name):
    number = positive(value, name)
    if not number.is_integer():
        raise ValueError(f"{name} must be a whole number of pixels")
    return int(number)


@dataclass(frozen=True)
class KnownObject:
    key: str
    name: str
    height_cm: float
    width_cm: float | None = None
    width_verified: bool = False


@dataclass(frozen=True)
class Calibration:
    focal_length_px: float
    frame_width: int
    frame_height: int

    def __post_init__(self):
        positive(self.focal_length_px, "focal_length_px")
        for name in ("frame_width", "frame_height"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")

    def check_frame(self, shape):
        if tuple(shape[:2]) != (self.frame_height, self.frame_width):
            raise ValueError(
                f"Calibration expects {self.frame_width}x{self.frame_height}; "
                f"received {shape[1]}x{shape[0]}. Recalibrate for this camera resolution."
            )


@dataclass(frozen=True)
class CameraConfig:
    source: str | int = field(repr=False)
    connect_timeout_s: float = 3.0
    read_timeout_s: float = 3.0
    stale_after_s: float = 1.0
    reconnect_delay_s: float = 0.5
    username: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class MeasurementConfig:
    backend: str = "grabcut"
    samples: int = 5
    jitter_px: int = 4
    edge_margin_px: int = 15
    width_correction: bool = False
    ratio_tolerance_pct: float = 20.0
    sam_weights: str = "models/mobile_sam.pt"


@dataclass(frozen=True)
class Settings:
    camera: CameraConfig
    calibration: Calibration
    measurement: MeasurementConfig
    objects: tuple[KnownObject, ...]


def load_settings(path, source_override=None):
    with Path(path).open("rb") as stream:
        raw = tomllib.load(stream)
    camera = raw.get("camera", {})
    source = source_override if source_override is not None else os.getenv(
        "PINGPONG_CAMERA_SOURCE", camera.get("source", 0)
    )
    if isinstance(source, str) and source.isdecimal():
        source = int(source)
    if not isinstance(source, (str, int)) or isinstance(source, bool):
        raise ValueError("Camera source must be a video path, HTTP URL or camera index")
    if isinstance(source, int) and source < 0:
        raise ValueError("Camera index cannot be negative")
    if isinstance(source, str) and source.startswith(("http://", "https://")):
        parsed = urlsplit(source)
        if not parsed.hostname:
            raise ValueError("Camera URL needs a hostname")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Keep camera credentials in PINGPONG_CAMERA_USERNAME/PASSWORD, not the URL")
    camera_cfg = CameraConfig(
        source=source,
        **{name: positive(camera.get(name, default), name) for name, default in (
            ("connect_timeout_s", 3), ("read_timeout_s", 3),
            ("stale_after_s", 1), ("reconnect_delay_s", 0.5),
        )},
        username=os.getenv("PINGPONG_CAMERA_USERNAME"),
        password=os.getenv("PINGPONG_CAMERA_PASSWORD"),
    )
    c = raw.get("calibration", {})
    calibration = Calibration(
        positive(c.get("focal_length_px", 1390), "focal_length_px"),
        pixel_count(c.get("frame_width", 1920), "frame_width"),
        pixel_count(c.get("frame_height", 1080), "frame_height"),
    )
    m = raw.get("measurement", {})
    measurement = MeasurementConfig(**m)
    if measurement.backend not in {"grabcut", "sam"}:
        raise ValueError("backend must be grabcut or sam")
    if isinstance(measurement.samples, bool) or not isinstance(measurement.samples, int) or not 1 <= measurement.samples <= 15:
        raise ValueError("samples must be between 1 and 15")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0
           for v in (measurement.jitter_px, measurement.edge_margin_px)):
        raise ValueError("jitter_px and edge_margin_px cannot be negative")
    positive(measurement.ratio_tolerance_pct, "ratio_tolerance_pct")
    objects = []
    for item in raw.get("objects", []):
        key, name = str(item["key"]), str(item["name"]).strip()
        if len(key) != 1 or not key.isdigit() or not name:
            raise ValueError("Each object needs a single digit key and a name")
        width = item.get("width_cm")
        objects.append(KnownObject(
            key, name, positive(item["height_cm"], "height_cm"),
            positive(width, "width_cm") if width is not None else None,
            bool(item.get("width_verified", False)),
        ))
    if not objects or len({o.key for o in objects}) != len(objects):
        raise ValueError("Provide at least one object with unique selection keys")
    return Settings(camera_cfg, calibration, measurement, tuple(objects))
