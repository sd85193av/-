import unittest
from pathlib import Path

from gesture_mouse.config import load_config


class ConfigTests(unittest.TestCase):
    def test_project_config_loads(self):
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        config = load_config(config_path)
        self.assertTrue(config.gestures.scroll_only)
        self.assertTrue(
            config.gestures.scroll_direction_lock_until_release
        )
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
