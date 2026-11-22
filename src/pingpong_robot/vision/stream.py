"""Latest-frame acquisition with bounded HTTP reads and stale-frame rejection."""

from dataclasses import dataclass
import threading
import time
from pathlib import Path
import cv2
import numpy as np
import requests
from ..config import CameraConfig


class JpegFrames:
    """Extract JPEGs across arbitrary MJPEG network chunks without growing forever."""

    def __init__(self, max_bytes=8 * 1024 * 1024):
        self.buffer = bytearray()
        self.max_bytes = max_bytes

    def feed(self, chunk):
        self.buffer.extend(chunk)
        frames = []
        while True:
            start = self.buffer.find(b"\xff\xd8")
            if start < 0:
                self.buffer[:] = self.buffer[-1:]
                break
            if start:
                del self.buffer[:start]
            end = self.buffer.find(b"\xff\xd9", 2)
            if end < 0:
                if len(self.buffer) > self.max_bytes:
                    self.buffer[:] = self.buffer[-1:]
                break
            if end + 2 <= self.max_bytes:
                frames.append(bytes(self.buffer[:end + 2]))
            del self.buffer[:end + 2]
        return frames


@dataclass(frozen=True)
class FramePacket:
    image: np.ndarray
    captured_at: float
    sequence: int


class CameraStream:
    """One acquisition thread, one newest frame, no credentials in status text.

    HTTP sources must provide MJPEG, as IP Webcam's /video endpoint does.
    Native USB/video capture uses OpenCV; backend read interruption varies by OS.
    """

    def __init__(self, config: CameraConfig):
        self.config = config
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._packet = None
        self._sequence = 0
        self._status = "Connecting to camera..."
        self._response = None
        self._thread = None

    @property
    def status(self):
        with self._lock:
            return self._status

    def _set_status(self, message):
        with self._lock:
            self._status = message

    def _publish(self, frame):
        if frame is None or frame.size == 0:
            return
        with self._lock:
            self._sequence += 1
            self._packet = FramePacket(frame.copy(), time.monotonic(), self._sequence)
            self._status = "Live"

    def latest(self, now=None):
        clock = time.monotonic() if now is None else now
        with self._lock:
            packet = self._packet
            if packet is None or clock - packet.captured_at > self.config.stale_after_s:
                return None
            return FramePacket(packet.image.copy(), packet.captured_at, packet.sequence)

    def start(self):
        if self._thread is not None:
            raise RuntimeError("CameraStream instances can only be started once")
        self._thread = threading.Thread(target=self._run, name="camera-reader", daemon=True)
        self._thread.start()
        return self

    def _run(self):
        source = self.config.source
        if isinstance(source, str) and source.startswith(("http://", "https://")):
            self._http_loop()
        else:
            self._native_loop()

    def _http_loop(self):
        auth = None
        if self.config.username is not None:
            auth = (self.config.username, self.config.password or "")
        with requests.Session() as session:
            session.trust_env = False
            while not self._stop.is_set():
                try:
                    with session.get(
                        self.config.source, stream=True, auth=auth,
                        timeout=(self.config.connect_timeout_s, self.config.read_timeout_s),
                    ) as response:
                        self._response = response
                        if response.status_code in (401, 403):
                            self._set_status("Camera rejected login; check local credentials")
                            return
                        response.raise_for_status()
                        parser = JpegFrames()
                        for chunk in response.iter_content(chunk_size=8192):
                            if self._stop.is_set():
                                return
                            for jpeg in parser.feed(chunk):
                                frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                                self._publish(frame)
                        self._set_status("Stream ended; reconnecting...")
                except requests.RequestException:
                    # Exceptions can contain URLs: keep diagnostics generic.
                    self._set_status("Camera connection lost; reconnecting...")
                finally:
                    self._response = None
                self._stop.wait(self.config.reconnect_delay_s)

    def _native_loop(self):
        source = self.config.source
        is_file = isinstance(source, str) and Path(source).is_file()
        while not self._stop.is_set():
            cap = cv2.VideoCapture(source)
            try:
                if not cap.isOpened():
                    self._set_status("Cannot open camera/video; check local source")
                else:
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    period = 1 / fps if is_file and 0 < fps < 1000 else 0
                    while not self._stop.is_set():
                        start = time.monotonic()
                        ok, frame = cap.read()
                        if not ok:
                            break
                        self._publish(frame)
                        if period:
                            self._stop.wait(max(0, period - (time.monotonic() - start)))
                    if is_file:
                        self._set_status("End of video; press Q to quit")
                        return
                    self._set_status("Camera disconnected; reconnecting...")
            finally:
                cap.release()
            self._stop.wait(self.config.reconnect_delay_s)

    def close(self):
        self._stop.set()
        response = self._response
        if response is not None:
            response.close()
        if self._thread is not None:
            self._thread.join(timeout=self.config.read_timeout_s + self.config.connect_timeout_s + 1)

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.close()
