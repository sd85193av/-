import unittest
from pathlib import Path

from gesture_mouse.config import load_config


class ConfigTests(unittest.TestCase):
    def test_project_config_loads(self):
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        config = load_config(config_path)
        self.assertTrue(config.gestures.scroll_only)
        self.assertTrue(config.gestures.pointer_enabled)
        self.assertTrue(config.gestures.thumb_click_enabled)
        self.assertLess(
            config.gestures.thumb_click_release_threshold,
            config.gestures.thumb_click_open_threshold,
        )
        self.assertFalse(
            config.gestures.scroll_direction_lock_until_release
        )
        self.assertTrue(
            config.gestures.scroll_return_motion_suppression
        )
        self.assertEqual(
            config.gestures.scroll_down_activation_distance,
            config.gestures.scroll_activation_distance,
        )
        self.assertEqual(
            config.gestures.scroll_down_step_distance,
            config.gestures.scroll_step_distance,
        )
        self.assertEqual(
            config.gestures.scroll_down_wheel_multiplier,
            1.0,
        )
        self.assertGreater(config.gestures.scroll_output_smoothing, 0.0)
        self.assertGreater(config.gestures.scroll_idle_reset_seconds, 0.0)
        self.assertEqual(
            config.display.detail_follow_window_title,
            "ChatGPT",
        )
        self.assertEqual(config.display.detail_monitor_index, 1)
        self.assertLessEqual(
            config.gestures.scroll_wheel_delta,
            config.gestures.scroll_max_wheel_delta,
        )


if __name__ == "__main__":
    unittest.main()
