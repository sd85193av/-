import unittest

from gesture_mouse.config import GestureConfig
from gesture_mouse.geometry import GestureMetrics
from gesture_mouse.gestures import GestureEngine, GestureEvent


def metrics(
    *,
    index_ratio=1.0,
    middle_ratio=1.0,
    index_extended=True,
    open_palm=False,
    closed_fist=False,
    two_finger=False,
    wrist=(0.5, 0.7),
):
    return GestureMetrics(
        control_point=(0.5, 0.4),
        wrist=wrist,
        index_pinch_ratio=index_ratio,
        middle_pinch_ratio=middle_ratio,
        index_extended=index_extended,
        open_palm=open_palm,
        middle_extended=two_finger,
        closed_fist=closed_fist,
        motion_point=wrist,
        two_finger_gesture=two_finger,
    )


class GestureEngineTests(unittest.TestCase):
    def setUp(self):
        self.config = GestureConfig()
        self.engine = GestureEngine(self.config)

    def test_short_index_pinch_does_not_click(self):
        self.engine.update(metrics(index_ratio=0.2), 1.0)
        result = self.engine.update(metrics(index_ratio=0.8), 1.1)
        self.assertNotIn(GestureEvent.LEFT_CLICK, result.events)

    def test_fist_clicks_once_until_released(self):
        fist_results = [
            self.engine.update(
                metrics(index_extended=False, closed_fist=True),
                1.0 + index * 0.06,
            )
            for index in range(6)
        ]
        held = self.engine.update(
            metrics(index_extended=False, closed_fist=True),
            1.4,
        )
        self.engine.update(metrics(index_extended=False), 1.5)
        second_fist_results = [
            self.engine.update(
                metrics(index_extended=False, closed_fist=True),
                2.0 + index * 0.06,
            )
            for index in range(6)
        ]
        self.assertNotIn(GestureEvent.LEFT_CLICK, fist_results[0].events)
        self.assertIn(GestureEvent.LEFT_CLICK, fist_results[-1].events)
        self.assertNotIn(GestureEvent.LEFT_CLICK, held.events)
        self.assertIn(GestureEvent.LEFT_CLICK, second_fist_results[-1].events)

    def test_held_index_pinch_drags(self):
        self.engine.update(metrics(index_ratio=0.2), 1.0)
        held = self.engine.update(metrics(index_ratio=0.2), 1.5)
        released = self.engine.update(metrics(index_ratio=0.8), 1.6)
        self.assertIn(GestureEvent.LEFT_DOWN, held.events)
        self.assertIn(GestureEvent.LEFT_UP, released.events)

    def test_middle_pinch_right_clicks_once_until_released(self):
        first = self.engine.update(metrics(middle_ratio=0.2), 1.0)
        held = self.engine.update(metrics(middle_ratio=0.2), 1.1)
        self.assertIn(GestureEvent.RIGHT_CLICK, first.events)
        self.assertNotIn(GestureEvent.RIGHT_CLICK, held.events)

    def test_two_finger_left_swipe_means_next(self):
        results = [
            self.engine.update(metrics(two_finger=True, wrist=point), now)
            for point, now in (
                ((0.75, 0.7), 1.0),
                ((0.50, 0.7), 1.1),
                ((0.45, 0.7), 1.2),
                ((0.35, 0.7), 1.3),
            )
        ]
        self.assertTrue(
            any(GestureEvent.NEXT in result.events for result in results)
        )

    def test_two_finger_right_swipe_means_previous(self):
        results = [
            self.engine.update(metrics(two_finger=True, wrist=point), now)
            for point, now in (
                ((0.25, 0.7), 1.0),
                ((0.50, 0.7), 1.1),
                ((0.55, 0.7), 1.2),
                ((0.65, 0.7), 1.3),
            )
        ]
        self.assertTrue(
            any(GestureEvent.PREVIOUS in result.events for result in results)
        )

    def test_two_finger_up_motion_scrolls_up(self):
        started = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.70)),
            1.0,
        )
        result = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.2,
        )
        self.assertFalse(started.cursor_active)
        self.assertIn(GestureEvent.SCROLL_UP, result.events)

    def test_two_finger_down_motion_scrolls_down(self):
        self.engine.update(metrics(two_finger=True, wrist=(0.5, 0.50)), 1.0)
        result = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.64)),
            1.2,
        )
        self.assertIn(GestureEvent.SCROLL_DOWN, result.events)

    def test_two_finger_short_dropout_keeps_motion_session(self):
        self.engine.update(metrics(two_finger=True, wrist=(0.5, 0.70)), 1.0)
        dropout = self.engine.update(
            metrics(index_extended=False, two_finger=False),
            1.1,
        )
        resumed = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.18,
        )
        self.assertEqual(dropout.mode, "TWO-FINGER HOLD")
        self.assertFalse(dropout.cursor_active)
        self.assertIn(GestureEvent.SCROLL_UP, resumed.events)

    def test_small_rebound_does_not_reverse_scroll_direction(self):
        self.engine.update(metrics(two_finger=True, wrist=(0.5, 0.70)), 1.0)
        upward = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.2,
        )
        rebound = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.64)),
            1.3,
        )
        self.assertIn(GestureEvent.SCROLL_UP, upward.events)
        self.assertNotIn(GestureEvent.SCROLL_DOWN, rebound.events)

    def test_scroll_starts_within_one_moving_frame(self):
        self.engine.update(metrics(two_finger=True, wrist=(0.5, 0.70)), 1.0)
        moving = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.68)),
            1.04,
        )
        self.assertIn(GestureEvent.SCROLL_UP, moving.events)
        self.assertGreater(moving.scroll_wheel_delta, 0)

    def test_deliberate_downward_reversal_responds_quickly(self):
        self.engine.update(metrics(two_finger=True, wrist=(0.5, 0.70)), 1.0)
        upward = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.2,
        )
        locked = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.90)),
            1.25,
        )
        downward = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.95)),
            1.34,
        )
        self.assertIn(GestureEvent.SCROLL_UP, upward.events)
        self.assertNotIn(GestureEvent.SCROLL_DOWN, locked.events)
        self.assertIn(GestureEvent.SCROLL_DOWN, downward.events)

    def test_recent_two_finger_motion_suppresses_fist_click(self):
        self.engine.update(metrics(two_finger=True), 1.0)
        results = [
            self.engine.update(
                metrics(index_extended=False, closed_fist=True),
                1.25 + index * 0.04,
            )
            for index in range(6)
        ]
        self.assertTrue(
            all(GestureEvent.LEFT_CLICK not in result.events for result in results)
        )

    def test_open_palm_does_not_scroll_or_navigate(self):
        self.engine.update(metrics(open_palm=True, wrist=(0.75, 0.70)), 1.0)
        result = self.engine.update(
            metrics(open_palm=True, wrist=(0.50, 0.50)),
            1.2,
        )
        motion_events = {
            GestureEvent.NEXT,
            GestureEvent.PREVIOUS,
            GestureEvent.SCROLL_UP,
            GestureEvent.SCROLL_DOWN,
        }
        self.assertTrue(motion_events.isdisjoint(result.events))

    def test_lost_hand_releases_drag(self):
        self.engine.update(metrics(index_ratio=0.2), 1.0)
        self.engine.update(metrics(index_ratio=0.2), 1.5)
        result = self.engine.no_hand()
        self.assertIn(GestureEvent.LEFT_UP, result.events)


class ScrollOnlyGestureEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = GestureEngine(
            GestureConfig(
                scroll_only=True,
                scroll_direction_lock_until_release=True,
            )
        )

    def test_fist_pinch_and_cursor_are_disabled(self):
        fist_results = [
            self.engine.update(
                metrics(index_extended=False, closed_fist=True),
                1.0 + index * 0.06,
            )
            for index in range(8)
        ]
        pinch = self.engine.update(metrics(index_ratio=0.2), 2.0)
        held_pinch = self.engine.update(metrics(index_ratio=0.2), 2.5)
        normal = self.engine.update(metrics(index_extended=True), 3.0)
        all_results = [*fist_results, pinch, held_pinch, normal]
        self.assertTrue(all(result.events == () for result in all_results))
        self.assertTrue(
            all(not result.cursor_active for result in all_results)
        )

    def test_horizontal_two_finger_motion_does_not_navigate(self):
        results = [
            self.engine.update(metrics(two_finger=True, wrist=point), now)
            for point, now in (
                ((0.75, 0.70), 1.0),
                ((0.50, 0.70), 1.1),
                ((0.35, 0.70), 1.2),
            )
        ]
        navigation_events = {GestureEvent.NEXT, GestureEvent.PREVIOUS}
        self.assertTrue(
            all(navigation_events.isdisjoint(result.events) for result in results)
        )

    def test_vertical_two_finger_motion_still_scrolls(self):
        self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.70)),
            1.0,
        )
        upward = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.2,
        )
        self.assertEqual(upward.events, (GestureEvent.SCROLL_UP,))
        self.assertGreater(upward.scroll_wheel_delta, 0)

    def test_returning_down_after_up_does_not_scroll_down(self):
        self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.70)),
            1.0,
        )
        upward = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.2,
        )
        returning = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.76)),
            1.4,
        )
        upward_again = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.56)),
            1.6,
        )
        self.assertEqual(upward.events, (GestureEvent.SCROLL_UP,))
        self.assertEqual(returning.events, ())
        self.assertEqual(upward_again.events, (GestureEvent.SCROLL_UP,))

    def test_returning_up_after_down_does_not_scroll_up(self):
        self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.45)),
            1.0,
        )
        downward = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.60)),
            1.2,
        )
        returning = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.40)),
            1.4,
        )
        downward_again = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.62)),
            1.6,
        )
        self.assertEqual(downward.events, (GestureEvent.SCROLL_DOWN,))
        self.assertEqual(returning.events, ())
        self.assertEqual(
            downward_again.events,
            (GestureEvent.SCROLL_DOWN,),
        )

    def test_releasing_two_finger_pose_allows_direction_change(self):
        self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.70)),
            1.0,
        )
        self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.2,
        )
        self.engine.update(
            metrics(index_extended=False, two_finger=False),
            1.4,
        )
        self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.45)),
            1.5,
        )
        downward = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.62)),
            1.7,
        )
        self.assertEqual(downward.events, (GestureEvent.SCROLL_DOWN,))


if __name__ == "__main__":
    unittest.main()
