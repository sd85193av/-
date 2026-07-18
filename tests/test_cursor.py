import unittest

from gesture_mouse.config import CursorConfig
from gesture_mouse.cursor import CursorMapper


class CursorMapperTests(unittest.TestCase):
    def test_maps_roi_edges_to_screen_edges(self):
        config = CursorConfig(
            horizontal_margin=0.1,
            vertical_margin=0.2,
            smoothing=1.0,
            minimum_move_pixels=0.0,
        )
        mapper = CursorMapper(1920, 1080, config)
        self.assertEqual(mapper.map((0.1, 0.2)), (0, 0))
        self.assertEqual(mapper.map((0.9, 0.8)), (1919, 1079))

    def test_clamps_outside_roi(self):
        config = CursorConfig(smoothing=1.0, minimum_move_pixels=0.0)
        mapper = CursorMapper(100, 50, config)
        self.assertEqual(mapper.map((-1.0, 2.0)), (0, 49))


if __name__ == "__main__":
    unittest.main()
