import unittest
from types import SimpleNamespace

import numpy as np

from gesture_mouse.geometry import GestureMetrics
from gesture_mouse.gestures import GestureFrame
from gesture_mouse.tracking_view import (
    DETAIL_HEIGHT,
    DETAIL_WIDTH,
    create_tracking_view,
)


class TrackingViewTests(unittest.TestCase):
    def test_renders_detail_panel_with_hand(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        landmarks = [
            SimpleNamespace(
                x=0.38 + (index % 5) * 0.06,
                y=0.28 + (index // 5) * 0.09,
            )
            for index in range(21)
        ]
        metrics = GestureMetrics(
            control_point=(0.5, 0.4),
            wrist=(0.5, 0.7),
            index_pinch_ratio=0.22,
            middle_pinch_ratio=0.75,
            index_extended=True,
            open_palm=False,
            middle_extended=False,
            ring_extended=False,
            pinky_extended=False,
            palm_scale=0.2,
        )
        gesture_frame = GestureFrame(
            events=(),
            cursor_active=True,
            control_point=(0.5, 0.4),
            mode="MOVE",
        )

        result = create_tracking_view(
            frame,
            landmarks,
            metrics,
            gesture_frame,
            handedness="Right",
            handedness_score=0.97,
            cursor_position=(960, 540),
            latest_action="LEFT CLICK",
            fps=29.8,
            pinch_threshold=0.34,
            paused=False,
            control_enabled=True,
            show_landmark_numbers=True,
        )

        self.assertEqual(result.shape, (DETAIL_HEIGHT, DETAIL_WIDTH, 3))
        self.assertGreater(int(result.sum()), 0)

    def test_renders_no_hand_state(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = create_tracking_view(
            frame,
            None,
            None,
            None,
            handedness="",
            handedness_score=0.0,
            cursor_position=None,
            latest_action="",
            fps=0.0,
            pinch_threshold=0.34,
            paused=False,
            control_enabled=False,
            show_landmark_numbers=True,
        )
        self.assertEqual(result.shape, (DETAIL_HEIGHT, DETAIL_WIDTH, 3))


if __name__ == "__main__":
    unittest.main()
