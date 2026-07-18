from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum

from gesture_mouse.config import GestureConfig
from gesture_mouse.geometry import GestureMetrics, Point


class GestureEvent(str, Enum):
    LEFT_CLICK = "left_click"
    LEFT_DOWN = "left_down"
    LEFT_UP = "left_up"
    RIGHT_CLICK = "right_click"
    PREVIOUS = "previous"
    NEXT = "next"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"


@dataclass(frozen=True)
class GestureFrame:
    events: tuple[GestureEvent, ...]
    cursor_active: bool
    control_point: Point | None
    mode: str
    index_pinched: bool = False
    middle_pinched: bool = False
    scroll_wheel_delta: int = 0


@dataclass(frozen=True)
class MotionResult:
    event: GestureEvent
    wheel_delta: int = 0


class MotionGestureDetector:
    def __init__(self, config: GestureConfig) -> None:
        self.config = config
        self._samples: deque[tuple[float, float, float]] = deque()
        self._last_swipe_at = float("-inf")
        self._last_scroll_at = float("-inf")
        self._scroll_anchor_y: float | None = None
        self._axis: str | None = None
        self._vertical_direction: int | None = None
        self._reverse_direction: int | None = None
        self._reverse_started_at: float | None = None
        self._reverse_start_y: float | None = None
        self._reverse_frames = 0

    def reset(self) -> None:
        self._samples.clear()
        self._scroll_anchor_y = None
        self._axis = None
        self._vertical_direction = None
        self._reset_reverse_candidate()

    def _reset_reverse_candidate(self) -> None:
        self._reverse_direction = None
        self._reverse_started_at = None
        self._reverse_start_y = None
        self._reverse_frames = 0

    def _activation_distance(self, delta_y: float) -> float:
        if delta_y > 0:
            return self.config.scroll_down_activation_distance
        return self.config.scroll_activation_distance

    def _step_distance(self, direction: int) -> float:
        if direction > 0:
            return self.config.scroll_down_step_distance
        return self.config.scroll_step_distance

    def _wheel_delta(self, distance: float, direction: int) -> int:
        step_distance = self._step_distance(direction)
        speed_ratio = max(1.0, distance / step_distance)
        direction_multiplier = (
            self.config.scroll_down_wheel_multiplier
            if direction > 0
            else 1.0
        )
        return min(
            self.config.scroll_max_wheel_delta,
            round(
                self.config.scroll_wheel_delta
                * speed_ratio
                * direction_multiplier
            ),
        )

    def update(self, now: float, point: Point) -> MotionResult | None:
        self._samples.append((now, point[0], point[1]))
        if self._scroll_anchor_y is None:
            self._scroll_anchor_y = point[1]
        window_start = now - self.config.swipe_window_seconds
        while self._samples and self._samples[0][0] < window_start:
            self._samples.popleft()

        if len(self._samples) < 2:
            return None

        first_time, first_x, first_y = self._samples[0]
        duration = now - first_time
        delta_x = point[0] - first_x
        delta_y = point[1] - first_y
        if duration < self.config.motion_min_duration_seconds:
            return None

        axis_ratio = self.config.maximum_swipe_vertical_ratio
        if self._axis is None:
            if (
                not self.config.scroll_only
                and abs(delta_x) >= self.config.swipe_distance
                and abs(delta_y) <= abs(delta_x) * axis_ratio
            ):
                self._axis = "horizontal"
            elif (
                abs(delta_y) >= self._activation_distance(delta_y)
                and abs(delta_x) <= abs(delta_y) * axis_ratio
            ):
                self._axis = "vertical"

        if self._axis == "horizontal":
            if now - self._last_swipe_at < self.config.swipe_cooldown_seconds:
                return None
            self._last_swipe_at = now
            event = GestureEvent.NEXT if delta_x < 0 else GestureEvent.PREVIOUS
            self.reset()
            return MotionResult(event)

        if self._axis == "vertical" and self._scroll_anchor_y is not None:
            scroll_delta = point[1] - self._scroll_anchor_y
            if abs(scroll_delta) < min(
                self.config.scroll_step_distance,
                self.config.scroll_down_step_distance,
            ):
                return None
            direction = -1 if scroll_delta < 0 else 1
            if (
                self.config.scroll_direction_lock_until_release
                and self._vertical_direction is not None
                and direction != self._vertical_direction
            ):
                self._scroll_anchor_y = point[1]
                return None
            if (
                self._vertical_direction is not None
                and direction != self._vertical_direction
            ):
                if self.config.scroll_return_motion_suppression:
                    if self._reverse_direction != direction:
                        self._reverse_direction = direction
                        self._reverse_started_at = now
                        self._reverse_start_y = self._scroll_anchor_y
                        self._reverse_frames = 1
                    else:
                        self._reverse_frames += 1
                    reverse_duration = now - (
                        self._reverse_started_at
                        if self._reverse_started_at is not None
                        else now
                    )
                    reverse_distance = abs(
                        point[1]
                        - (
                            self._reverse_start_y
                            if self._reverse_start_y is not None
                            else point[1]
                        )
                    )
                    self._scroll_anchor_y = point[1]
                    if not (
                        reverse_duration
                        >= self.config.scroll_direction_switch_seconds
                        and reverse_distance
                        >= self.config.scroll_direction_switch_distance
                        and self._reverse_frames
                        >= self.config.scroll_direction_switch_min_frames
                    ):
                        return None
                    self._vertical_direction = direction
                    self._last_scroll_at = now
                    self._reset_reverse_candidate()
                    return MotionResult(
                        GestureEvent.SCROLL_UP
                        if direction < 0
                        else GestureEvent.SCROLL_DOWN,
                        self._wheel_delta(abs(scroll_delta), direction),
                    )
                if (
                    now - self._last_scroll_at
                    < self.config.scroll_reverse_lock_seconds
                    or abs(scroll_delta) < self.config.scroll_reverse_distance
                ):
                    return None
                self._scroll_anchor_y = point[1]
                self._vertical_direction = direction
                self._last_scroll_at = now
                return MotionResult(
                    GestureEvent.SCROLL_UP
                    if direction < 0
                    else GestureEvent.SCROLL_DOWN,
                    self._wheel_delta(abs(scroll_delta), direction),
                )
            self._reset_reverse_candidate()
            if abs(scroll_delta) < self._step_distance(direction):
                return None
            if (
                now - self._last_scroll_at
                < self.config.scroll_cooldown_seconds
            ):
                return None
            if self._vertical_direction is None:
                self._vertical_direction = direction
            if direction == self._vertical_direction:
                self._scroll_anchor_y = point[1]
            self._last_scroll_at = now
            return MotionResult(
                GestureEvent.SCROLL_UP
                if direction < 0
                else GestureEvent.SCROLL_DOWN,
                self._wheel_delta(abs(scroll_delta), direction),
            )
        return None


class GestureEngine:
    def __init__(self, config: GestureConfig) -> None:
        self.config = config
        self._index_pinched = False
        self._middle_pinched = False
        self._pinch_started_at = 0.0
        self._dragging = False
        self._fist_started_at: float | None = None
        self._fist_stable_frames = 0
        self._fist_latched = False
        self._last_fist_click_at = float("-inf")
        self._last_right_click_at = float("-inf")
        self._thumb_click_started_at: float | None = None
        self._thumb_click_stable_frames = 0
        self._thumb_click_latched = False
        self._last_thumb_click_at = float("-inf")
        self._last_two_finger_at = float("-inf")
        self._smoothed_motion_point: Point | None = None
        self._motion_session_active = False
        self._motion = MotionGestureDetector(config)

    def _pinch_with_hysteresis(self, ratio: float, was_pinched: bool) -> bool:
        threshold = self.config.pinch_threshold
        if was_pinched:
            threshold *= self.config.pinch_release_ratio
        return ratio <= threshold

    def _smooth_motion_point(self, point: Point) -> Point:
        if self._smoothed_motion_point is None:
            self._smoothed_motion_point = point
        else:
            alpha = self.config.motion_smoothing
            previous_x, previous_y = self._smoothed_motion_point
            self._smoothed_motion_point = (
                previous_x + (point[0] - previous_x) * alpha,
                previous_y + (point[1] - previous_y) * alpha,
            )
        return self._smoothed_motion_point

    def _reset_fist_candidate(self) -> None:
        self._fist_started_at = None
        self._fist_stable_frames = 0
        self._fist_latched = False

    def _reset_thumb_click(self) -> None:
        self._thumb_click_started_at = None
        self._thumb_click_stable_frames = 0
        self._thumb_click_latched = False

    def _thumb_click_triggered(
        self,
        metrics: GestureMetrics,
        now: float,
    ) -> bool:
        ratio = metrics.thumb_open_ratio
        if self._thumb_click_latched:
            if ratio <= self.config.thumb_click_release_threshold:
                self._reset_thumb_click()
            return False
        if ratio < self.config.thumb_click_open_threshold:
            self._thumb_click_started_at = None
            self._thumb_click_stable_frames = 0
            return False
        if self._thumb_click_started_at is None:
            self._thumb_click_started_at = now
        self._thumb_click_stable_frames += 1
        if (
            now - self._thumb_click_started_at
            >= self.config.thumb_click_hold_seconds
            and self._thumb_click_stable_frames
            >= self.config.thumb_click_min_frames
            and now - self._last_thumb_click_at
            >= self.config.thumb_click_cooldown_seconds
        ):
            self._thumb_click_latched = True
            self._last_thumb_click_at = now
            return True
        return False

    def _end_motion_session(self) -> None:
        self._motion.reset()
        self._smoothed_motion_point = None
        self._motion_session_active = False

    def reset(self) -> tuple[GestureEvent, ...]:
        events: list[GestureEvent] = []
        if self._dragging:
            events.append(GestureEvent.LEFT_UP)
        self._index_pinched = False
        self._middle_pinched = False
        self._dragging = False
        self._reset_fist_candidate()
        self._reset_thumb_click()
        self._last_two_finger_at = float("-inf")
        self._end_motion_session()
        return tuple(events)

    def no_hand(self) -> GestureFrame:
        events = self.reset()
        return GestureFrame(
            events=events,
            cursor_active=False,
            control_point=None,
            mode="NO HAND",
        )

    def update(self, metrics: GestureMetrics, now: float) -> GestureFrame:
        events: list[GestureEvent] = []
        is_two_finger = (
            metrics.two_finger_gesture and metrics.motion_point is not None
        )
        if is_two_finger:
            if self._dragging:
                events.append(GestureEvent.LEFT_UP)
                self._dragging = False
            self._index_pinched = False
            self._middle_pinched = False
            self._reset_fist_candidate()
            self._reset_thumb_click()
            self._last_two_finger_at = now
            self._motion_session_active = True
            smoothed_point = self._smooth_motion_point(metrics.motion_point)
            motion_result = self._motion.update(now, smoothed_point)
            if motion_result is not None:
                events.append(motion_result.event)
            mode = (
                motion_result.event.value.replace("_", " ").upper()
                if motion_result is not None
                else (
                    "TWO-FINGER SCROLL"
                    if self.config.scroll_only
                    else "TWO-FINGER MOTION"
                )
            )
            return GestureFrame(
                events=tuple(events),
                cursor_active=False,
                control_point=metrics.control_point,
                mode=mode,
                scroll_wheel_delta=(
                    motion_result.wheel_delta
                    if motion_result is not None
                    else 0
                ),
            )

        if (
            self._motion_session_active
            and now - self._last_two_finger_at
            <= self.config.two_finger_grace_seconds
        ):
            self._reset_fist_candidate()
            return GestureFrame(
                events=tuple(events),
                cursor_active=False,
                control_point=metrics.control_point,
                mode="TWO-FINGER HOLD",
            )

        if self._motion_session_active:
            self._end_motion_session()

        if self.config.scroll_only:
            self._index_pinched = False
            self._middle_pinched = False
            self._dragging = False
            self._reset_fist_candidate()
            pointer_active = (
                self.config.pointer_enabled
                and metrics.index_extended
                and not metrics.middle_extended
                and not metrics.ring_extended
                and not metrics.pinky_extended
                and not metrics.closed_fist
            )
            if (
                pointer_active
                and self.config.thumb_click_enabled
                and self._thumb_click_triggered(metrics, now)
            ):
                events.append(GestureEvent.LEFT_CLICK)
            elif not pointer_active:
                self._reset_thumb_click()
            return GestureFrame(
                events=tuple(events),
                cursor_active=pointer_active,
                control_point=metrics.control_point,
                mode=(
                    "THUMB CLICK"
                    if GestureEvent.LEFT_CLICK in events
                    else ("POINTER" if pointer_active else "SCROLL ONLY")
                ),
            )

        if metrics.closed_fist:
            if self._dragging:
                events.append(GestureEvent.LEFT_UP)
                self._dragging = False
            self._index_pinched = False
            self._middle_pinched = False
            self._motion.reset()
            if (
                now - self._last_two_finger_at
                < self.config.fist_after_motion_suppression_seconds
            ):
                self._reset_fist_candidate()
                return GestureFrame(
                    events=tuple(events),
                    cursor_active=False,
                    control_point=metrics.control_point,
                    mode="GESTURE TRANSITION",
                )
            if self._fist_started_at is None:
                self._fist_started_at = now
            self._fist_stable_frames += 1
            if (
                not self._fist_latched
                and now - self._fist_started_at >= self.config.fist_hold_seconds
                and self._fist_stable_frames
                >= self.config.fist_min_stable_frames
                and now - self._last_fist_click_at
                >= self.config.fist_click_cooldown_seconds
            ):
                events.append(GestureEvent.LEFT_CLICK)
                self._fist_latched = True
                self._last_fist_click_at = now
            return GestureFrame(
                events=tuple(events),
                cursor_active=False,
                control_point=metrics.control_point,
                mode="FIST CLICK" if GestureEvent.LEFT_CLICK in events else "FIST",
            )

        self._reset_fist_candidate()
        index_pinched = self._pinch_with_hysteresis(
            metrics.index_pinch_ratio,
            self._index_pinched,
        )

        if index_pinched and not self._index_pinched:
            self._pinch_started_at = now
            self._motion.reset()
        elif index_pinched and not self._dragging:
            if now - self._pinch_started_at >= self.config.drag_hold_seconds:
                self._dragging = True
                events.append(GestureEvent.LEFT_DOWN)
        elif not index_pinched and self._index_pinched:
            if self._dragging:
                events.append(GestureEvent.LEFT_UP)
                self._dragging = False

        middle_pinched = False
        if not index_pinched:
            middle_pinched = self._pinch_with_hysteresis(
                metrics.middle_pinch_ratio,
                self._middle_pinched,
            )
            if (
                middle_pinched
                and not self._middle_pinched
                and now - self._last_right_click_at
                >= self.config.right_click_cooldown_seconds
            ):
                events.append(GestureEvent.RIGHT_CLICK)
                self._last_right_click_at = now

        self._index_pinched = index_pinched
        self._middle_pinched = middle_pinched
        cursor_active = (
            (
                metrics.index_extended
                and not metrics.open_palm
                and not metrics.two_finger_gesture
            )
            or index_pinched
        )

        if self._dragging:
            mode = "DRAG"
        elif index_pinched:
            mode = "PINCH"
        elif middle_pinched:
            mode = "RIGHT CLICK"
        elif metrics.two_finger_gesture:
            mode = "TWO-FINGER MOTION"
        elif metrics.open_palm:
            mode = "OPEN PALM"
        elif cursor_active:
            mode = "MOVE"
        else:
            mode = "IDLE"

        return GestureFrame(
            events=tuple(events),
            cursor_active=cursor_active,
            control_point=metrics.control_point,
            mode=mode,
            index_pinched=index_pinched,
            middle_pinched=middle_pinched,
        )
