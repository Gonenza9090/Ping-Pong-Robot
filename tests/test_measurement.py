from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from pingpong_robot.brain.measurement import measure, refined_edges
from pingpong_robot.brain.segmentation import clicked_component
from pingpong_robot.cli import main
from pingpong_robot.config import Calibration, KnownObject, MeasurementConfig, load_settings


class FixedSegmenter:
    def segment(self, frame, point, roi):
        mask = np.zeros(frame.shape[:2], np.uint8)
        mask[0:20, 10:20] = 1
        return clicked_component(mask, point)


class MeasurementTests(unittest.TestCase):
    def test_object_touching_image_border_has_safe_edges(self):
        frame = np.zeros((30, 40, 3), np.uint8)
        frame[:20, 10:20] = 200
        x1, y1, x2, y2 = refined_edges(frame, (10, 0, 10, 20), margin=15)
        self.assertTrue(0 <= x1 < x2 <= 40)
        self.assertTrue(0 <= y1 < y2 <= 30)

    def test_pipeline_recovers_known_distance_from_controlled_mask(self):
        frame = np.zeros((30, 40, 3), np.uint8)
        config = MeasurementConfig(samples=5, jitter_px=0, edge_margin_px=0)
        result = measure(frame, (15, 10), (1, 0, 39, 29), FixedSegmenter(), config,
                         Calibration(100, 40, 30), KnownObject("1", "Test", 20))
        self.assertEqual(result.distance_cm, 100)
        self.assertEqual(result.samples_used, 5)
        self.assertEqual(result.method, "height_only")

    def test_invalid_click_and_resolution_fail_before_segmentation(self):
        frame = np.zeros((30, 40, 3), np.uint8)
        with self.assertRaises(ValueError):
            measure(frame, (50, 50), (1, 0, 39, 29), FixedSegmenter(), MeasurementConfig())
        with self.assertRaises(ValueError):
            measure(frame, (15, 10), (1, 0, 39, 29), FixedSegmenter(), MeasurementConfig(),
                    Calibration(100, 400, 300), KnownObject("1", "Test", 20))

    def test_calibration_command_writes_reusable_multi_sample_json(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "calibration.local.json"
            code = main(["calibrate", "--sample", "20", "100", "200",
                         "--sample", "10", "200", "50", "--frame-size", "1600", "900",
                         "--output", str(path)])
            self.assertEqual(code, 0)
            data = json.loads(path.read_text())
            self.assertEqual(data["focal_length_px"], 1000)
            self.assertEqual(data["frame_width"], 1600)
            self.assertEqual(len(data["samples"]), 2)

    def test_example_preserves_dimensions_without_enabling_unverified_widths(self):
        settings = load_settings(Path(__file__).resolve().parents[1] / "config.example.toml")
        self.assertFalse(settings.measurement.width_correction)
        self.assertEqual((settings.calibration.frame_width, settings.calibration.frame_height), (1920, 1080))
        self.assertEqual({o.name: o.width_cm for o in settings.objects},
                         {"Fogg can": 4.4, "Box": 10.0, "Can 2": 3.5})
        self.assertTrue(all(not o.width_verified for o in settings.objects))
        from pingpong_robot.config import CameraConfig
        hidden = CameraConfig(source="http://localhost/video", username="private-user", password="private-value")
        self.assertNotIn("private-user", repr(hidden))
        self.assertNotIn("private-value", repr(hidden))


if __name__ == "__main__":
    unittest.main()
