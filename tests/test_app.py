from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from pingpong_robot.app import RobotApp
from pingpong_robot.config import load_settings
from pingpong_robot.vision.stream import FramePacket
from pingpong_robot.vision.viewport import render_view


class AppTests(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings(Path(__file__).resolve().parents[1] / 'config.example.toml')
        self.app = RobotApp(self.settings, 'measure')

    def tearDown(self):
        self.app.executor.shutdown(wait=True, cancel_futures=True)

    def test_click_freezes_the_displayed_raw_frame_before_next_capture(self):
        frame = np.full((1080, 1920, 3), 90, np.uint8)
        self.app._display(FramePacket(frame, 0, 1), 'Live')
        self.app.object = self.settings.objects[0]
        self.app._click(cv2.EVENT_LBUTTONDOWN, 640, 360, 0, None)
        self.assertEqual(self.app.phase, 'preview')
        self.assertEqual(self.app.point, (960, 540))
        frame[:] = 220
        self.assertTrue(np.all(self.app.frozen == 90))

    def test_resolution_error_happens_before_loading_a_model(self):
        self.app.settings = replace(self.settings, measurement=replace(self.settings.measurement, backend='sam'))
        with patch('pingpong_robot.app.make_segmenter') as loader:
            with self.assertRaises(ValueError):
                self.app._job(np.zeros((480, 640, 3), np.uint8), (100, 100), (20, 20, 200, 200), self.settings.objects[0])
            loader.assert_not_called()

    def test_stale_camera_frame_cannot_be_frozen(self):
        self.app._display(None, 'Disconnected')
        self.app.object = self.settings.objects[0]
        self.app._click(cv2.EVENT_LBUTTONDOWN, 100, 100, 0, None)
        self.assertEqual(self.app.phase, 'live')
        self.assertIsNone(self.app.frozen)


if __name__ == '__main__':
    unittest.main()
