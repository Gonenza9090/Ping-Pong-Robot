import math
import unittest
from pingpong_robot.brain.geometry import distance_cm, focal_length_px, resolve_height
from pingpong_robot.config import Calibration, KnownObject


class GeometryTests(unittest.TestCase):
    def test_calibration_and_distance_round_trip_for_several_objects_and_ranges(self):
        for real_height in (12, 17.5, 18.8):
            for distance in (80, 100, 205, 450):
                pixel_height = real_height * 1390 / distance
                focal = focal_length_px(real_height, distance, pixel_height)
                self.assertAlmostEqual(focal, 1390)
                self.assertAlmostEqual(distance_cm(real_height, focal, pixel_height), distance)

    def test_zero_negative_nan_and_infinity_are_not_distances(self):
        for invalid in (0, -1, math.nan, math.inf, True):
            with self.assertRaises(ValueError):
                distance_cm(17.5, 1390, invalid)

    def test_unverified_width_can_never_override_a_height(self):
        obj = KnownObject("1", "Test object", 12, width_cm=3.5, width_verified=False)
        result = resolve_height(249, 72, obj, use_width=True)
        self.assertEqual(result.height_px, 249)
        self.assertEqual(result.method, "height_only")

    def test_verified_width_fallback_requires_explicit_opt_in(self):
        obj = KnownObject("1", "Test object", 20, width_cm=5, width_verified=True)
        self.assertEqual(resolve_height(20, 25, obj).height_px, 20)
        result = resolve_height(20, 25, obj, use_width=True)
        self.assertEqual(result.height_px, 100)
        self.assertEqual(result.method, "experimental_width_fallback")

    def test_resolution_mismatch_is_rejected_instead_of_silently_scaling(self):
        calibration = Calibration(1390, 1600, 900)
        calibration.check_frame((900, 1600, 3))
        with self.assertRaises(ValueError):
            calibration.check_frame((720, 1280, 3))


if __name__ == "__main__":
    unittest.main()
