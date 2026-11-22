"""One interactive desktop app for the original Video/Pixel/Distance workflows."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import textwrap
import cv2
import numpy as np
from .vision.stream import CameraStream
from .vision.viewport import render_view
from .brain.segmentation import clamp_box, make_segmenter
from .brain.measurement import measure


class RobotApp:
    def __init__(self, settings, mode, log_path="outputs/measurements.jsonl", actual_distance=None):
        self.settings, self.command = settings, mode
        self.log_path, self.actual_distance = Path(log_path), actual_distance
        self.phase = "live"
        self.zoom = 1.0
        self.frame = self.viewport = self.frozen = self.point = None
        self.object = None
        self.half_width, self.half_height = 120, 220
        self.result = None
        self.message = ""
        self.future = None
        self.segmenter = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="segmentation")
        self.window = "Ping Pong Robot | Vision + Brain prototype"

    def _click(self, event, x, y, flags, unused):
        if event != cv2.EVENT_LBUTTONDOWN or self.command == "view" or self.phase != "live":
            return
        if self.frame is None or self.viewport is None:
            self.message = "Wait for a fresh camera frame"
            return
        if self.command == "measure" and self.object is None:
            self.message = "Select the calibrated object using its number key first"
            return
        # This exact displayed raw frame is frozen; never substitute the next frame.
        self.frozen = self.frame.copy()
        self.point = self.viewport.to_raw(x, y)
        self.phase, self.result = "preview", None
        self.message = "Adjust the box to contain the object, then press ENTER"

    def _job(self, frame, point, roi, obj):
        calibration = self.settings.calibration if self.command == "measure" else None
        if calibration is not None:
            calibration.check_frame(frame.shape)
        if self.segmenter is None:
            self.segmenter = make_segmenter(self.settings.measurement.backend, self.settings.measurement.sam_weights)
        return measure(frame, point, roi, self.segmenter, self.settings.measurement,
                       calibration, obj if calibration is not None else None)

    def _submit(self):
        roi = clamp_box(self.point, self.half_width, self.half_height, self.frozen.shape)
        self.future = self.executor.submit(self._job, self.frozen.copy(), self.point, roi, self.object)
        self.phase, self.message = "busy", "Segmenting the frozen frame... Q to quit"

    def _poll(self):
        if self.future is None or not self.future.done():
            return
        try:
            self.result = self.future.result()
            r = self.result
            self.message = f"{r.samples_used} samples; height spread {r.height_spread_px:.1f}px; {r.method}"
        except Exception as error:
            self.result = None
            self.message = f"Measurement failed: {error}"
        self.future = None
        self.phase = "result"

    @staticmethod
    def _labels(image, lines, *, bottom=False):
        wrapped = []
        limit = max(18, image.shape[1] // 9)
        for line in lines:
            wrapped.extend(textwrap.wrap(str(line), width=limit) or [""])
        height = min(image.shape[0], 22 * len(wrapped) + 12)
        y0 = image.shape[0] - height if bottom else 0
        shade = image.copy()
        cv2.rectangle(shade, (0, y0), (image.shape[1], y0 + height), (25, 25, 25), -1)
        cv2.addWeighted(shade, .8, image, .2, 0, image)
        for index, line in enumerate(wrapped):
            cv2.putText(image, line, (9, y0 + 22 * (index + 1)),
                        cv2.FONT_HERSHEY_SIMPLEX, .52, (240, 240, 240), 1, cv2.LINE_AA)

    def _display(self, packet, status):
        if self.phase == "live":
            self.frame = None if packet is None else packet.image
            frame = self.frame
        else:
            frame = self.frozen
        if frame is None:
            self.viewport = None
            image = np.zeros((360, 640, 3), np.uint8)
            self._labels(image, [status, "Q = quit; waiting for fresh frames"])
            return image
        image, view = render_view(frame, self.zoom)
        if self.phase == "live":
            self.viewport = view
        if self.phase in {"preview", "busy"}:
            x1, y1, x2, y2 = clamp_box(self.point, self.half_width, self.half_height, frame.shape)
            cv2.rectangle(image, view.to_display(x1, y1), view.to_display(x2 - 1, y2 - 1), (255, 220, 0), 1)
            cv2.drawMarker(image, view.to_display(*self.point), (0, 0, 255), cv2.MARKER_CROSS, 14, 2)
        if self.result is not None and self.phase == "result":
            r = self.result
            x1, y1, x2, y2 = r.bbox
            cv2.rectangle(image, view.to_display(x1, y1), view.to_display(x2 - 1, y2 - 1), (0, 255, 0), 2)
            cv2.circle(image, view.to_display(*r.centroid), 4, (0, 0, 255), -1)
        selected = "none" if self.object is None else self.object.name
        menu = " | ".join(f"{o.key}: {o.name}" for o in self.settings.objects)
        top = [f"Mode: {self.command} | {self.settings.measurement.backend} | display zoom {self.zoom:.1f}x",
               f"Object: {selected} | {menu}"]
        if self.phase == "result" and self.result is not None:
            r = self.result
            label = f"Raw height {r.raw_height_px:.1f}px; width {r.raw_width_px:.1f}px"
            if r.distance_cm is not None:
                label += f" | Distance {r.distance_cm:.1f}cm"
            top.append(label)
        self._labels(image, top)
        controls = {
            "live": "Click = freeze | Z/X = display zoom | Q = quit",
            "preview": "+/- = box size | ENTER = segment | ESC = cancel | Q = quit",
            "busy": "Processing; the interface remains responsive | Q = quit",
            "result": "R = retry | S = save result | SPACE = live | Q = quit",
        }
        self._labels(image, [self.message or status, controls[self.phase]], bottom=True)
        return image

    def _save(self):
        if self.result is None:
            self.message = "No measurement to save"
            return
        row = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mode": self.command,
            "object": None if self.object is None else self.object.name,
            "object_height_cm": None if self.object is None else self.object.height_cm,
            "object_width_cm": None if self.object is None else self.object.width_cm,
            "width_verified": False if self.object is None else self.object.width_verified,
            "frame_width": self.frozen.shape[1], "frame_height": self.frozen.shape[0],
            "backend": self.settings.measurement.backend,
            "calibration_focal_px": self.settings.calibration.focal_length_px if self.command == "measure" else None,
            "measurement": asdict(self.result),
            "actual_distance_cm": self.actual_distance,
        }
        if self.actual_distance is not None and self.result.distance_cm is not None:
            row["absolute_error_cm"] = abs(self.result.distance_cm - self.actual_distance)
            row["relative_error_pct"] = row["absolute_error_cm"] / self.actual_distance * 100
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")
        self.message = f"Saved measurement to {self.log_path}"

    def run(self):
        try:
            with CameraStream(self.settings.camera) as stream:
                cv2.namedWindow(self.window, cv2.WINDOW_AUTOSIZE)
                cv2.setMouseCallback(self.window, self._click)
                while True:
                    self._poll()
                    cv2.imshow(self.window, self._display(stream.latest(), stream.status))
                    key = cv2.waitKey(20) & 0xFF
                    if key in (ord("q"), ord("Q")) or cv2.getWindowProperty(self.window, cv2.WND_PROP_VISIBLE) < 1:
                        break
                    if self.phase == "live":
                        for obj in self.settings.objects:
                            if key == ord(obj.key):
                                self.object = obj
                        if key == ord("z"):
                            self.zoom = min(3, self.zoom + .5)
                        elif key == ord("x"):
                            self.zoom = max(1, self.zoom - .5)
                    elif self.phase == "preview":
                        if key in (ord("+"), ord("=")):
                            self.half_width += 10; self.half_height += 10
                        elif key == ord("-"):
                            self.half_width = max(10, self.half_width - 10)
                            self.half_height = max(10, self.half_height - 10)
                        elif key in (10, 13):
                            self._submit()
                        elif key == 27:
                            self.phase = "live"
                    elif self.phase == "result":
                        if key == ord("r"):
                            self.result = None; self.phase = "preview"
                        elif key == ord("s"):
                            try:
                                self._save()
                            except OSError:
                                self.message = "Could not save result; check the output directory"
                        elif key in (32, 27):
                            self.result = None; self.phase = "live"
        finally:
            cv2.destroyAllWindows()
            if self.future is not None and not self.future.done():
                print("Finishing the current segmentation before exiting...")
            self.executor.shutdown(wait=True, cancel_futures=True)
