from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CameraConfig:
    index: int = 0
    width: int = 960
    height: int = 540
    fps: int = 30
    detection_confidence: float = 0.65
    presence_confidence: float = 0.60
    tracking_confidence: float = 0.60


@dataclass(frozen=True)
class CursorConfig:
    horizontal_margin: float = 0.12
    vertical_margin: float = 0.12
    smoothing: float = 0.35
    minimum_move_pixels: float = 1.5


@dataclass(frozen=True)
class GestureConfig:
    scroll_only: bool = False
    pointer_enabled: bool = False
    pinch_threshold: float = 0.34
    pinch_release_ratio: float = 1.40
    drag_hold_seconds: float = 0.35
    fist_hold_seconds: float = 0.25
    fist_min_stable_frames: int = 6
    fist_click_cooldown_seconds: float = 0.35
    fist_after_motion_suppression_seconds: float = 0.45
    right_click_cooldown_seconds: float = 0.55
    swipe_distance: float = 0.18
    swipe_window_seconds: float = 0.55
    swipe_cooldown_seconds: float = 0.90
    maximum_swipe_vertical_ratio: float = 0.70
    motion_smoothing: float = 0.65
    motion_min_duration_seconds: float = 0.02
    two_finger_grace_seconds: float = 0.15
    scroll_activation_distance: float = 0.012
    scroll_step_distance: float = 0.004
    scroll_down_activation_distance: float = 0.012
    scroll_down_step_distance: float = 0.004
    scroll_down_wheel_multiplier: float = 1.0
    scroll_cooldown_seconds: float = 0.02
    scroll_wheel_delta: int = 30
    scroll_max_wheel_delta: int = 90
    scroll_direction_lock_until_release: bool = False
    scroll_return_motion_suppression: bool = False
    scroll_direction_switch_seconds: float = 0.22
    scroll_direction_switch_distance: float = 0.06
    scroll_direction_switch_min_frames: int = 4
    scroll_reverse_lock_seconds: float = 0.08
    scroll_reverse_distance: float = 0.018


@dataclass(frozen=True)
class DisplayConfig:
    preview: bool = True
    show_landmarks: bool = True
    always_on_top: bool = False
    detail_window: bool = True
    detail_always_on_top: bool = False
    show_landmark_numbers: bool = True
    detail_follow_window_title: str = "ChatGPT"
    detail_monitor_index: int = 1
    detail_window_width: int = 560
    detail_window_height: int = 720


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig
    cursor: CursorConfig
    gestures: GestureConfig
    display: DisplayConfig
    navigation_mode: str = "browser"
    activation_delay_seconds: float = 2.0


def _construct(cls: type[Any], data: dict[str, Any], section: str) -> Any:
    try:
        return cls(**data)
    except TypeError as exc:
        raise ValueError(f"設定區段 '{section}' 有未知或無效的欄位：{exc}") from exc


def _validate(config: AppConfig) -> None:
    if config.camera.index < 0:
        raise ValueError("camera.index 不可小於 0")
    if config.camera.width < 320 or config.camera.height < 240:
        raise ValueError("camera 解析度至少需為 320x240")
    for name in (
        "detection_confidence",
        "presence_confidence",
        "tracking_confidence",
    ):
        value = getattr(config.camera, name)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"camera.{name} 必須介於 0 與 1")
    if not 0.0 <= config.cursor.horizontal_margin < 0.45:
        raise ValueError("cursor.horizontal_margin 必須介於 0 與 0.45")
    if not 0.0 <= config.cursor.vertical_margin < 0.45:
        raise ValueError("cursor.vertical_margin 必須介於 0 與 0.45")
    if not 0.01 <= config.cursor.smoothing <= 1.0:
        raise ValueError("cursor.smoothing 必須介於 0.01 與 1")
    if config.gestures.pinch_threshold <= 0:
        raise ValueError("gestures.pinch_threshold 必須大於 0")
    if config.gestures.pinch_release_ratio <= 1:
        raise ValueError("gestures.pinch_release_ratio 必須大於 1")
    if config.gestures.fist_hold_seconds < 0.05:
        raise ValueError("gestures.fist_hold_seconds 不可小於 0.05")
    if not 2 <= config.gestures.fist_min_stable_frames <= 30:
        raise ValueError("gestures.fist_min_stable_frames 必須介於 2 與 30")
    if not 0.05 <= config.gestures.two_finger_grace_seconds <= 0.50:
        raise ValueError("gestures.two_finger_grace_seconds 必須介於 0.05 與 0.50")
    if not 0.05 <= config.gestures.motion_smoothing <= 1.0:
        raise ValueError("gestures.motion_smoothing 必須介於 0.05 與 1")
    if not 0.0 <= config.gestures.motion_min_duration_seconds <= 0.10:
        raise ValueError("motion_min_duration_seconds 必須介於 0 與 0.10")
    if not 0.002 <= config.gestures.scroll_step_distance <= 0.10:
        raise ValueError("gestures.scroll_step_distance 必須介於 0.002 與 0.10")
    if config.gestures.scroll_activation_distance < config.gestures.scroll_step_distance:
        raise ValueError("scroll_activation_distance 不可小於 scroll_step_distance")
    if not 0.002 <= config.gestures.scroll_down_step_distance <= 0.10:
        raise ValueError(
            "gestures.scroll_down_step_distance 必須介於 0.002 與 0.10"
        )
    if (
        config.gestures.scroll_down_activation_distance
        < config.gestures.scroll_down_step_distance
    ):
        raise ValueError(
            "scroll_down_activation_distance 不可小於 "
            "scroll_down_step_distance"
        )
    if not 0.5 <= config.gestures.scroll_down_wheel_multiplier <= 3.0:
        raise ValueError(
            "gestures.scroll_down_wheel_multiplier 必須介於 0.5 與 3.0"
        )
    if not 0.05 <= config.gestures.scroll_direction_switch_seconds <= 1.0:
        raise ValueError(
            "gestures.scroll_direction_switch_seconds 必須介於 0.05 與 1.0"
        )
    if not 0.01 <= config.gestures.scroll_direction_switch_distance <= 0.30:
        raise ValueError(
            "gestures.scroll_direction_switch_distance 必須介於 0.01 與 0.30"
        )
    if not 2 <= config.gestures.scroll_direction_switch_min_frames <= 30:
        raise ValueError(
            "gestures.scroll_direction_switch_min_frames 必須介於 2 與 30"
        )
    if not 10 <= config.gestures.scroll_wheel_delta <= 120:
        raise ValueError("gestures.scroll_wheel_delta 必須介於 10 與 120")
    if not (
        config.gestures.scroll_wheel_delta
        <= config.gestures.scroll_max_wheel_delta
        <= 240
    ):
        raise ValueError("scroll_max_wheel_delta 必須介於基礎值與 240")
    if config.display.detail_monitor_index < 0:
        raise ValueError("display.detail_monitor_index 不可小於 0")
    if len(config.display.detail_follow_window_title) > 200:
        raise ValueError(
            "display.detail_follow_window_title must be at most 200 characters"
        )
    if config.display.detail_window_width < 320:
        raise ValueError("display.detail_window_width 不可小於 320")
    if config.display.detail_window_height < 360:
        raise ValueError("display.detail_window_height 不可小於 360")
    if config.navigation_mode not in {"browser", "arrows", "page"}:
        raise ValueError("navigation_mode 僅支援 browser、arrows 或 page")


def load_config(path: Path) -> AppConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"找不到設定檔：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"設定檔 JSON 格式錯誤（第 {exc.lineno} 行）：{exc.msg}") from exc

    config = AppConfig(
        camera=_construct(CameraConfig, raw.get("camera", {}), "camera"),
        cursor=_construct(CursorConfig, raw.get("cursor", {}), "cursor"),
        gestures=_construct(GestureConfig, raw.get("gestures", {}), "gestures"),
        display=_construct(DisplayConfig, raw.get("display", {}), "display"),
        navigation_mode=raw.get("navigation_mode", "browser"),
        activation_delay_seconds=float(raw.get("activation_delay_seconds", 2.0)),
    )
    _validate(config)
    return config
