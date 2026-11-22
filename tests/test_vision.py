import unittest
import cv2
import numpy as np
from pingpong_robot.config import CameraConfig
from pingpong_robot.vision.stream import CameraStream, JpegFrames
from pingpong_robot.vision.viewport import render_view
from pingpong_robot.brain.segmentation import clicked_component, clamp_box, GrabCutSegmenter
from pingpong_robot.brain.measurement import refined_edges


class VisionTests(unittest.TestCase):
    def test_flat_image_does_not_invent_edge_offsets(self):
        image = np.full((120, 160, 3), 200, np.uint8)
        self.assertEqual(refined_edges(image, (65, 30, 30, 60)), (65, 30, 95, 90))

    def test_zoom_keeps_clicked_raw_coordinate_and_raw_pixels_unchanged(self):
        original = np.zeros((901, 1601, 3), dtype=np.uint8)
        before = original.copy()
        for zoom in (1, 1.5, 2, 2.5, 3):
            display, viewport = render_view(original, zoom)
            point = (viewport.x0 + viewport.crop_width // 2,
                     viewport.y0 + viewport.crop_height // 2)
            restored = viewport.to_raw(*viewport.to_display(*point))
            self.assertLessEqual(abs(restored[0] - point[0]), 2)
            self.assertLessEqual(abs(restored[1] - point[1]), 2)
            self.assertLessEqual(display.shape[1], 1280)
            self.assertLessEqual(display.shape[0], 720)
        np.testing.assert_array_equal(original, before)

    def test_clicked_small_object_wins_over_large_unrelated_foreground(self):
        mask = np.zeros((100, 100), np.uint8)
        mask[5:80, 5:60] = 1
        mask[60:80, 75:90] = 1
        selected = clicked_component(mask, (80, 70))
        self.assertEqual(selected.bbox, (75, 60, 15, 20))
        self.assertIsNone(clicked_component(mask, (95, 95)))

    def test_mjpeg_decoder_handles_split_markers_multiple_frames_and_noise(self):
        image = np.full((30, 40, 3), 180, np.uint8)
        ok, encoded = cv2.imencode(".jpg", image)
        self.assertTrue(ok)
        payload = encoded.tobytes()
        parser = JpegFrames()
        chunks = [b"header\r\n" + payload[:1], payload[1:20], payload[20:] + payload[:5], payload[5:]]
        frames = [frame for chunk in chunks for frame in parser.feed(chunk)]
        self.assertEqual(len(frames), 2)
        for frame in frames:
            decoded = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
            self.assertEqual(decoded.shape, image.shape)

    def test_broken_mjpeg_frame_does_not_grow_buffer_forever(self):
        parser = JpegFrames(max_bytes=128)
        parser.feed(b"\xff\xd8" + b"x" * 1000)
        self.assertLessEqual(len(parser.buffer), 128)

    def test_old_frame_is_not_returned_after_camera_disconnect(self):
        stream = CameraStream(CameraConfig(source=0, stale_after_s=.5))
        stream._publish(np.zeros((20, 30, 3), np.uint8))
        fresh = stream.latest()
        self.assertIsNotNone(fresh)
        self.assertIsNone(stream.latest(now=fresh.captured_at + .51))
        fresh.image[:] = 255
        self.assertFalse(stream.latest().image.any())

    def test_prompt_boxes_are_clipped_with_exclusive_upper_bounds(self):
        self.assertEqual(clamp_box((0, 0), 20, 20, (40, 60, 3)), (0, 0, 21, 21))
        self.assertEqual(clamp_box((59, 39), 20, 20, (40, 60, 3)), (39, 19, 60, 40))

    def test_grabcut_segments_a_synthetic_object_without_camera_or_ml_weights(self):
        image = np.full((120, 160, 3), 220, np.uint8)
        image[30:90, 65:95] = (0, 0, 180)
        result = GrabCutSegmenter().segment(image, (80, 60), (50, 15, 110, 105))
        self.assertIsNotNone(result)
        self.assertEqual(result.bbox, (65, 30, 30, 60))


if __name__ == "__main__":
    unittest.main()
