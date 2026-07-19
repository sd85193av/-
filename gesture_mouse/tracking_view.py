from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

from gesture_mouse.geometry import GestureMetrics, LandmarkLike
from gesture_mouse.gestures import GestureFrame
from gesture_mouse.overlay import draw_landmarks


DETAIL_WIDTH = 560
DETAIL_HEIGHT = 720
PREVIEW_TOP = 46
PREVIEW_HEIGHT = 360


def _fit_image(image: np.ndarray, width: int, height: int) -> np.ndarray:
    canvas = np.full((height, width, 3), 18, dtype=np.uint8)
    source_height, source_width = image.shape[:2]
    scale = min(width / source_width, height / source_height)
    target_width = max(1, round(source_width * scale))
    target_height = max(1, round(source_height * scale))
    resized = cv2.resize(
        image,
        (target_width, target_height),
        interpolation=cv2.INTER_LINEAR,
    )
    offset_x = (width - target_width) // 2
    offset_y = (height - target_height) // 2
    canvas[
        offset_y : offset_y + target_height,
        offset_x : offset_x + target_width,
    ] = resized
    return canvas


def _hand_crop(
    frame: np.ndarray,
    landmarks: Sequence[LandmarkLike],
    show_indices: bool,
) -> np.ndarray:
    annotated = frame.copy()
    draw_landmarks(annotated, landmarks, show_indices=show_indices)
    height, width = frame.shape[:2]
    xs = [item.x * width for item in landmarks]
    ys = [item.y * height for item in landmarks]
    hand_width = max(xs) - min(xs)
    hand_height = max(ys) - min(ys)
    padding = max(hand_width, hand_height) * 0.32 + 24
    left = max(0, round(min(xs) - padding))
    right = min(width, round(max(xs) + padding))
    top = max(0, round(min(ys) - padding))
    bottom = min(height, round(max(ys) + padding))
    if right <= left or bottom <= top:
        return annotated
    return annotated[top:bottom, left:right]


def _put_text(
    canvas: np.ndarray,
    text: str,
    x: int,
    y: int,
    *,
    scale: float = 0.52,
    color: tuple[int, int, int] = (225, 225, 225),
    thickness: int = 1,
) -> None:
    cv2.putText(
        canvas,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def _metric_bar(
    canvas: np.ndarray,
    label: str,
    value: float,
    threshold: float,
    y: int,
    *,
    active_above: bool = False,
) -> None:
    left = 178
    width = 330
    maximum = 1.20
    fill = round(min(value / maximum, 1.0) * width)
    threshold_x = left + round(min(threshold / maximum, 1.0) * width)
    active = value >= threshold if active_above else value <= threshold
    color = (70, 210, 110) if active else (70, 150, 235)
    _put_text(canvas, label, 24, y + 13, scale=0.48)
    cv2.rectangle(canvas, (left, y), (left + width, y + 16), (65, 65, 65), -1)
    cv2.rectangle(canvas, (left, y), (left + fill, y + 16), color, -1)
    cv2.line(
        canvas,
        (threshold_x, y - 4),
        (threshold_x, y + 20),
        (255, 255, 255),
        1,
    )
    _put_text(
        canvas,
        (
            f"{value:.2f}  {'OPEN' if active else 'CLOSED'}"
            if active_above
            else f"{value:.2f}  {'PINCHED' if active else 'OPEN'}"
        ),
        left + 6,
        y + 14,
        scale=0.40,
        color=(20, 20, 20) if fill > 145 else (235, 235, 235),
        thickness=1,
    )


def create_tracking_view(
    camera_frame: np.ndarray,
    landmarks: Sequence[LandmarkLike] | None,
    metrics: GestureMetrics | None,
    gesture_frame: GestureFrame | None,
    *,
    handedness: str,
    handedness_score: float,
    cursor_position: tuple[int, int] | None,
    latest_action: str,
    fps: float,
    pinch_threshold: float,
    pinky_open_threshold: float,
    paused: bool,
    control_enabled: bool,
    show_landmark_numbers: bool,
) -> np.ndarray:
    canvas = np.full((DETAIL_HEIGHT, DETAIL_WIDTH, 3), 24, dtype=np.uint8)
    cv2.rectangle(canvas, (0, 0), (DETAIL_WIDTH, 40), (12, 12, 12), -1)
    _put_text(
        canvas,
        "HAND TRACKING DETAILS",
        18,
        28,
        scale=0.66,
        color=(80, 220, 255),
        thickness=2,
    )

    if landmarks:
        close_up = _hand_crop(camera_frame, landmarks, show_landmark_numbers)
        preview = _fit_image(close_up, DETAIL_WIDTH, PREVIEW_HEIGHT)
    else:
        preview = np.full((PREVIEW_HEIGHT, DETAIL_WIDTH, 3), 18, dtype=np.uint8)
        _put_text(
            preview,
            "NO HAND DETECTED",
            154,
            190,
            scale=0.72,
            color=(90, 90, 255),
            thickness=2,
        )
    canvas[PREVIEW_TOP : PREVIEW_TOP + PREVIEW_HEIGHT] = preview

    mode = "PAUSED" if paused else (gesture_frame.mode if gesture_frame else "NO HAND")
    mode_color = (90, 90, 255) if paused else (80, 220, 255)
    _put_text(canvas, f"MODE  {mode}", 24, 438, scale=0.68, color=mode_color, thickness=2)
    control_text = "ACTIVE" if control_enabled and not paused else "SAFE / PAUSED"
    _put_text(canvas, f"CONTROL  {control_text}", 330, 438, scale=0.46)

    hand_text = "--"
    if handedness:
        hand_text = f"{handedness.upper()}  {handedness_score * 100:.0f}%"
    _put_text(canvas, f"HAND  {hand_text}", 24, 470)
    _put_text(canvas, f"FPS  {fps:4.1f}", 330, 470)
    cursor_text = "--" if cursor_position is None else f"{cursor_position[0]}, {cursor_position[1]}"
    _put_text(canvas, f"CURSOR  {cursor_text}", 24, 500)
    if latest_action:
        _put_text(
            canvas,
            f"ACTION  {latest_action}",
            280,
            500,
            color=(255, 200, 80),
            thickness=2,
        )

    if metrics is not None:
        _metric_bar(
            canvas,
            "INDEX PINCH",
            metrics.index_pinch_ratio,
            pinch_threshold,
            526,
        )
        _metric_bar(
            canvas,
            "PINKY OPEN",
            metrics.pinky_open_ratio,
            pinky_open_threshold,
            562,
            active_above=True,
        )
        fingers = (
            ("I", metrics.index_extended),
            ("M", metrics.middle_extended),
            ("R", metrics.ring_extended),
            ("P", metrics.pinky_extended),
        )
        _put_text(canvas, "FINGERS", 24, 617)
        x = 124
        for label, extended in fingers:
            color = (70, 210, 110) if extended else (90, 90, 100)
            cv2.circle(canvas, (x, 610), 13, color, -1)
            _put_text(
                canvas,
                label,
                x - 5,
                616,
                scale=0.42,
                color=(20, 20, 20),
                thickness=2,
            )
            x += 48
        if metrics.closed_fist:
            palm_text = "CLOSED FIST"
            palm_color = (80, 200, 255)
        elif metrics.two_finger_gesture:
            palm_text = "2-FINGER MOVE"
            palm_color = (100, 220, 170)
        elif metrics.open_palm:
            palm_text = "OPEN PALM"
            palm_color = (100, 220, 170)
        else:
            palm_text = "POINTER / PINCH"
            palm_color = (100, 220, 170)
        _put_text(canvas, palm_text, 344, 617, color=palm_color)
    else:
        _put_text(canvas, "Waiting for hand metrics...", 24, 554, color=(150, 150, 150))

    cv2.line(canvas, (20, 648), (DETAIL_WIDTH - 20, 648), (75, 75, 75), 1)
    _put_text(
        canvas,
        "Landmarks: 0=wrist, 8=index, 12=middle, 20=pinky",
        24,
        674,
        scale=0.43,
        color=(185, 185, 185),
    )
    _put_text(
        canvas,
        "F9 hide details | F8 pause | ESC quit",
        24,
        704,
        scale=0.48,
        color=(220, 220, 220),
    )
    return canvas
