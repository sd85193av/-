from __future__ import annotations

from typing import Sequence

import cv2

from gesture_mouse.config import CursorConfig
from gesture_mouse.geometry import LandmarkLike


HAND_CONNECTIONS = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),
)


def draw_landmarks(
    frame,
    landmarks: Sequence[LandmarkLike],
    *,
    show_indices: bool = False,
) -> None:
    height, width = frame.shape[:2]
    pixels = [
        (round(item.x * width), round(item.y * height)) for item in landmarks
    ]
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, pixels[start], pixels[end], (60, 210, 130), 2)
    for index, location in enumerate(pixels):
        color = (0, 215, 255) if index in {4, 8, 12} else (255, 220, 80)
        radius = 6 if index in {4, 8, 12} else 3
        cv2.circle(frame, location, radius, color, -1)
        if show_indices:
            cv2.putText(
                frame,
                str(index),
                (location[0] + 5, location[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.40,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )


def draw_roi(frame, config: CursorConfig) -> None:
    height, width = frame.shape[:2]
    top_left = (
        round(config.horizontal_margin * width),
        round(config.vertical_margin * height),
    )
    bottom_right = (
        round((1.0 - config.horizontal_margin) * width),
        round((1.0 - config.vertical_margin) * height),
    )
    cv2.rectangle(frame, top_left, bottom_right, (120, 120, 120), 1)


def draw_status(
    frame,
    status: str,
    fps: float,
    paused: bool,
    control_enabled: bool,
    latest_action: str,
) -> None:
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width, 76), (20, 20, 20), -1)
    status_color = (80, 210, 255)
    if paused:
        status = "PAUSED"
        status_color = (80, 80, 255)
    elif not control_enabled:
        status = f"SAFE TEST - {status}"
        status_color = (80, 220, 120)

    cv2.putText(
        frame,
        status,
        (18, 31),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.78,
        status_color,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"FPS {fps:4.1f}",
        (width - 125, 29),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )
    if latest_action:
        cv2.putText(
            frame,
            latest_action,
            (18, 62),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 200, 80),
            2,
            cv2.LINE_AA,
        )
    cv2.rectangle(frame, (0, height - 34), (width, height), (20, 20, 20), -1)
    cv2.putText(
        frame,
        "ESC quit | F8 pause | F9 details | 2 fingers=vertical scroll only",
        (12, height - 11),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        (225, 225, 225),
        1,
        cv2.LINE_AA,
    )
