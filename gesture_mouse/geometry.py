from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, Sequence


class LandmarkLike(Protocol):
    x: float
    y: float


Point = tuple[float, float]


@dataclass(frozen=True)
class GestureMetrics:
    control_point: Point
    wrist: Point
    index_pinch_ratio: float
    middle_pinch_ratio: float
    index_extended: bool
    open_palm: bool
    middle_extended: bool = False
    ring_extended: bool = False
    pinky_extended: bool = False
    palm_scale: float = 0.0
    closed_fist: bool = False
    motion_point: Point | None = None
    two_finger_gesture: bool = False


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point(landmarks: Sequence[LandmarkLike], index: int) -> Point:
    item = landmarks[index]
    return float(item.x), float(item.y)


def finger_extended(
    landmarks: Sequence[LandmarkLike],
    tip_index: int,
    pip_index: int,
    mcp_index: int,
) -> bool:
    wrist = point(landmarks, 0)
    tip = point(landmarks, tip_index)
    pip = point(landmarks, pip_index)
    mcp = point(landmarks, mcp_index)
    return (
        distance(tip, wrist) > distance(pip, wrist) * 1.10
        and distance(tip, mcp) > distance(pip, mcp)
    )


def finger_curled(
    landmarks: Sequence[LandmarkLike],
    tip_index: int,
    pip_index: int,
    mcp_index: int,
) -> bool:
    wrist = point(landmarks, 0)
    tip = point(landmarks, tip_index)
    pip = point(landmarks, pip_index)
    mcp = point(landmarks, mcp_index)
    return (
        distance(tip, wrist) <= distance(pip, wrist) * 1.05
        and distance(tip, mcp) <= distance(pip, mcp) * 1.55
    )


def analyze_landmarks(landmarks: Sequence[LandmarkLike]) -> GestureMetrics:
    if len(landmarks) != 21:
        raise ValueError(f"預期 21 個手部關節點，實際收到 {len(landmarks)} 個")

    wrist = point(landmarks, 0)
    thumb_tip = point(landmarks, 4)
    index_tip = point(landmarks, 8)
    middle_tip = point(landmarks, 12)

    palm_scale = max(
        distance(point(landmarks, 5), point(landmarks, 17)),
        distance(wrist, point(landmarks, 9)),
        1e-6,
    )
    index_extended = finger_extended(landmarks, 8, 6, 5)
    middle_extended = finger_extended(landmarks, 12, 10, 9)
    ring_extended = finger_extended(landmarks, 16, 14, 13)
    pinky_extended = finger_extended(landmarks, 20, 18, 17)
    closed_fist = all(
        (
            finger_curled(landmarks, 8, 6, 5),
            finger_curled(landmarks, 12, 10, 9),
            finger_curled(landmarks, 16, 14, 13),
            finger_curled(landmarks, 20, 18, 17),
        )
    )

    return GestureMetrics(
        control_point=index_tip,
        wrist=wrist,
        index_pinch_ratio=distance(thumb_tip, index_tip) / palm_scale,
        middle_pinch_ratio=distance(thumb_tip, middle_tip) / palm_scale,
        index_extended=index_extended,
        open_palm=(
            index_extended and middle_extended and ring_extended and pinky_extended
        ),
        middle_extended=middle_extended,
        ring_extended=ring_extended,
        pinky_extended=pinky_extended,
        palm_scale=palm_scale,
        closed_fist=closed_fist,
        motion_point=(
            (index_tip[0] + middle_tip[0]) / 2.0,
            (index_tip[1] + middle_tip[1]) / 2.0,
        ),
        two_finger_gesture=(
            index_extended
            and middle_extended
            and not ring_extended
            and not pinky_extended
        ),
    )
