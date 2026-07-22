import unittest
from pathlib import Path

from gesture_mouse.config import GestureConfig, load_config
from gesture_mouse.geometry import GestureMetrics
from gesture_mouse.gestures import (
    GestureEngine,
    GestureEvent,
    MotionGestureDetector,
)


def metrics(
    *,
    index_ratio=1.0,
    middle_ratio=1.0,
    index_extended=True,
    open_palm=False,
    closed_fist=False,
    two_finger=False,
    thumb_ratio=0.0,
    wrist=(0.5, 0.7),
):
    return GestureMetrics(
        control_point=(0.5, 0.4),
        wrist=wrist,
        index_pinch_ratio=index_ratio,
        middle_pinch_ratio=middle_ratio,
        index_extended=index_extended,
        open_palm=open_palm,
        thumb_open_ratio=thumb_ratio,
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

    def test_two_finger_dropout_resyncs_without_jump(self):
        engine = GestureEngine(
            GestureConfig(scroll_idle_reset_seconds=0.14)
        )
        engine.update(metrics(two_finger=True, wrist=(0.5, 0.70)), 1.0)
        dropout = engine.update(
            metrics(index_extended=False, two_finger=False),
            1.1,
        )
        resumed = engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.18,
        )
        continued = engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.54)),
            1.22,
        )
        self.assertEqual(dropout.mode, "TWO-FINGER HOLD")
        self.assertFalse(dropout.cursor_active)
        self.assertEqual(resumed.events, ())
        self.assertIn(GestureEvent.SCROLL_UP, continued.events)
        self.assertLess(
            continued.scroll_wheel_delta,
            engine.config.scroll_max_wheel_delta,
        )

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
                scroll_return_motion_suppression=True,
                scroll_direction_switch_seconds=0.22,
                scroll_direction_switch_distance=0.06,
                scroll_direction_switch_min_frames=4,
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

    def test_index_only_moves_pointer_without_clicking(self):
        engine = GestureEngine(
            GestureConfig(
                scroll_only=True,
                pointer_enabled=True,
                scroll_return_motion_suppression=True,
            )
        )
        pointer = engine.update(metrics(index_extended=True), 1.0)
        two_finger = engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.5)),
            1.2,
        )
        fist = engine.update(
            metrics(index_extended=False, closed_fist=True),
            1.4,
        )
        self.assertTrue(pointer.cursor_active)
        self.assertEqual(pointer.mode, "POINTER")
        self.assertEqual(pointer.events, ())
        self.assertFalse(two_finger.cursor_active)
        self.assertFalse(fist.cursor_active)
        self.assertEqual(fist.events, ())

    def test_outward_thumb_clicks_once_until_retracted(self):
        engine = GestureEngine(
            GestureConfig(
                scroll_only=True,
                pointer_enabled=True,
                thumb_click_enabled=True,
                thumb_click_open_threshold=1.20,
                thumb_click_release_threshold=1.05,
                thumb_click_hold_seconds=0.10,
                thumb_click_min_frames=3,
                thumb_click_cooldown_seconds=0.35,
            )
        )
        opening = [
            engine.update(metrics(thumb_ratio=1.35), now)
            for now in (1.00, 1.06, 1.12)
        ]
        held = engine.update(metrics(thumb_ratio=1.35), 1.20)
        engine.update(metrics(thumb_ratio=0.90), 1.30)
        reopened = [
            engine.update(metrics(thumb_ratio=1.35), now)
            for now in (1.50, 1.56, 1.62)
        ]
        self.assertNotIn(GestureEvent.LEFT_CLICK, opening[0].events)
        self.assertIn(GestureEvent.LEFT_CLICK, opening[-1].events)
        self.assertNotIn(GestureEvent.LEFT_CLICK, held.events)
        self.assertIn(GestureEvent.LEFT_CLICK, reopened[-1].events)

    def test_thumb_does_not_click_during_two_finger_scroll(self):
        engine = GestureEngine(
            GestureConfig(
                scroll_only=True,
                pointer_enabled=True,
                thumb_click_enabled=True,
                thumb_click_open_threshold=1.20,
                thumb_click_release_threshold=1.05,
                thumb_click_hold_seconds=0.10,
                thumb_click_min_frames=3,
            )
        )
        results = [
            engine.update(
                metrics(
                    two_finger=True,
                    thumb_ratio=1.50,
                    wrist=(0.5, 0.70 - index * 0.02),
                ),
                1.0 + index * 0.06,
            )
            for index in range(5)
        ]
        self.assertTrue(
            all(
                GestureEvent.LEFT_CLICK not in result.events
                for result in results
            )
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

    @staticmethod
    def _smooth_detector() -> MotionGestureDetector:
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        return MotionGestureDetector(load_config(config_path).gestures)

    def test_diagonal_motion_still_scrolls_in_scroll_only_mode(self):
        detector = self._smooth_detector()
        detector.update(1.000, (0.50, 0.50))
        result = detector.update(1.033, (0.51, 0.49))
        self.assertIsNotNone(result)
        self.assertEqual(result.event, GestureEvent.SCROLL_UP)

    def test_scroll_starts_at_base_delta_instead_of_maximum(self):
        detector = self._smooth_detector()
        detector.update(1.000, (0.50, 0.50))
        result = detector.update(1.033, (0.50, 0.48))
        self.assertIsNotNone(result)
        self.assertEqual(result.wheel_delta, 24)
        self.assertLess(result.wheel_delta, 72)

    def test_equal_up_and_down_motion_have_equal_output(self):
        upward = self._smooth_detector()
        downward = self._smooth_detector()
        upward.update(1.000, (0.50, 0.50))
        downward.update(1.000, (0.50, 0.50))
        up_result = upward.update(1.033, (0.50, 0.49))
        down_result = downward.update(1.033, (0.50, 0.51))
        self.assertEqual(up_result.wheel_delta, down_result.wheel_delta)

    def test_fast_motion_ramps_output_without_a_sudden_jump(self):
        detector = self._smooth_detector()
        detector.update(1.000, (0.50, 0.50))
        first = detector.update(1.033, (0.50, 0.49))
        second = detector.update(1.066, (0.50, 0.47))
        third = detector.update(1.099, (0.50, 0.45))
        self.assertLess(first.wheel_delta, second.wheel_delta)
        self.assertLess(second.wheel_delta, third.wheel_delta)
        self.assertLessEqual(third.wheel_delta, 72)

    def test_multiframe_return_to_origin_never_scrolls_reverse(self):
        detector = self._smooth_detector()
        detector.update(1.000, (0.50, 0.70))
        upward = detector.update(1.033, (0.50, 0.68))
        detector.update(1.066, (0.50, 0.62))
        returning = [
            detector.update(now, (0.50, y))
            for now, y in (
                (1.099, 0.63),
                (1.132, 0.64),
                (1.165, 0.65),
                (1.198, 0.66),
                (1.231, 0.67),
                (1.264, 0.68),
                (1.297, 0.69),
                (1.330, 0.70),
            )
        ]
        upward_again = detector.update(1.363, (0.50, 0.68))
        self.assertEqual(upward.event, GestureEvent.SCROLL_UP)
        self.assertTrue(
            all(
                result is None or result.event != GestureEvent.SCROLL_DOWN
                for result in returning
            )
        )
        self.assertEqual(upward_again.event, GestureEvent.SCROLL_UP)

    def test_reverse_switch_requires_motion_beyond_origin(self):
        detector = self._smooth_detector()
        detector.update(1.000, (0.50, 0.70))
        detector.update(1.033, (0.50, 0.68))
        detector.update(1.066, (0.50, 0.60))
        results = [
            detector.update(now, (0.50, y))
            for now, y in (
                (1.099, 0.64),
                (1.132, 0.68),
                (1.165, 0.71),
                (1.198, 0.73),
                (1.231, 0.75),
                (1.264, 0.76),
            )
        ]
        self.assertTrue(
            all(
                result is None or result.event != GestureEvent.SCROLL_DOWN
                for result in results[:-1]
            )
        )
        self.assertEqual(results[-1].event, GestureEvent.SCROLL_DOWN)

    def test_stationary_tracking_noise_does_not_scroll(self):
        detector = self._smooth_detector()
        results = [
            detector.update(
                1.000 + index * 0.033,
                (0.50, 0.50 + (0.001 if index % 2 else -0.001)),
            )
            for index in range(12)
        ]
        self.assertTrue(all(result is None for result in results))

    def test_total_scroll_is_stable_across_frame_rates(self):
        totals = []
        for fps in (15, 30, 60):
            detector = self._smooth_detector()
            frame_count = round(0.6 * fps)
            results = [
                detector.update(
                    index / fps,
                    (0.50, 0.70 - 0.18 * index / frame_count),
                )
                for index in range(frame_count + 1)
            ]
            totals.append(
                sum(result.wheel_delta for result in results if result)
            )
        self.assertLess(max(totals) / min(totals), 1.15)

    def test_small_downward_motion_is_more_sensitive_and_continuous(self):
        engine = GestureEngine(
            GestureConfig(
                scroll_only=True,
                scroll_direction_lock_until_release=True,
                scroll_down_activation_distance=0.008,
                scroll_down_step_distance=0.002,
                scroll_down_wheel_multiplier=1.15,
            )
        )
        engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.500)),
            1.0,
        )
        first = engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.513)),
            1.04,
        )
        second = engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.520)),
            1.08,
        )
        self.assertEqual(first.events, (GestureEvent.SCROLL_DOWN,))
        self.assertEqual(second.events, (GestureEvent.SCROLL_DOWN,))
        self.assertGreater(first.scroll_wheel_delta, 0)
        self.assertGreater(second.scroll_wheel_delta, 0)

    def test_same_small_upward_motion_keeps_original_threshold(self):
        engine = GestureEngine(
            GestureConfig(
                scroll_only=True,
                scroll_direction_lock_until_release=True,
                scroll_down_activation_distance=0.008,
                scroll_down_step_distance=0.002,
                scroll_down_wheel_multiplier=1.15,
            )
        )
        engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.500)),
            1.0,
        )
        small_upward = engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.487)),
            1.04,
        )
        self.assertEqual(small_upward.events, ())

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

    def test_sustained_reverse_switches_direction_without_release(self):
        self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.70)),
            1.0,
        )
        upward = self.engine.update(
            metrics(two_finger=True, wrist=(0.5, 0.58)),
            1.2,
        )
        reverse_results = [
            self.engine.update(metrics(two_finger=True, wrist=point), now)
            for point, now in (
                ((0.5, 0.70), 1.30),
                ((0.5, 0.78), 1.40),
                ((0.5, 0.86), 1.50),
                ((0.5, 0.92), 1.56),
            )
        ]
        self.assertEqual(upward.events, (GestureEvent.SCROLL_UP,))
        self.assertTrue(
            all(result.events == () for result in reverse_results[:-1])
        )
        self.assertEqual(
            reverse_results[-1].events,
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
