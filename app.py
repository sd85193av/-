from __future__ import annotations

import argparse
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from gesture_mouse import __version__
from gesture_mouse.config import AppConfig, load_config
from gesture_mouse.cursor import CursorMapper
from gesture_mouse.geometry import analyze_landmarks
from gesture_mouse.gestures import GestureEngine, GestureEvent
from gesture_mouse.overlay import draw_landmarks, draw_roi, draw_status
from gesture_mouse.tracking_view import create_tracking_view
from gesture_mouse.windows_input import WindowsInput


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_ROOT / "config.json"
MODEL_PATH = PROJECT_ROOT / "models" / "hand_landmarker.task"
CAMERA_WINDOW_NAME = "Gesture Mouse - Camera Angle"
DETAIL_WINDOW_NAME = "Gesture Mouse - Tracking Details"


def configure_logging() -> logging.Logger:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    logger = logging.getLogger("gesture_mouse")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_dir / "gesture_mouse.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用攝影機手勢控制 Windows 鼠標")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--camera", type=int, help="覆寫攝影機編號")
    parser.add_argument(
        "--no-control",
        action="store_true",
        help="只顯示辨識結果，不控制鼠標或鍵盤",
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="不顯示攝影機預覽視窗",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="檢查環境、設定與模型後退出",
    )
    parser.add_argument(
        "--camera-test",
        action="store_true",
        help="擷取攝影機畫面以測試裝置後退出",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser.parse_args()


def build_landmarker(config: AppConfig):
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"找不到手部辨識模型：{MODEL_PATH}")
    # MediaPipe's Windows native layer cannot reliably open non-ASCII paths.
    # Passing the bytes keeps Chinese project-folder names fully supported.
    model_bytes = MODEL_PATH.read_bytes()
    options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_buffer=model_bytes),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=config.camera.detection_confidence,
        min_hand_presence_confidence=config.camera.presence_confidence,
        min_tracking_confidence=config.camera.tracking_confidence,
    )
    return mp.tasks.vision.HandLandmarker.create_from_options(options)


def open_camera(config: AppConfig, camera_override: int | None):
    camera_index = config.camera.index if camera_override is None else camera_override
    capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not capture.isOpened():
        capture.release()
        capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise RuntimeError(
            f"無法開啟攝影機 {camera_index}。請確認鏡頭未被其他程式占用，"
            "並允許 Windows 的相機權限。"
        )
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera.height)
    capture.set(cv2.CAP_PROP_FPS, config.camera.fps)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


def diagnose(config: AppConfig, controller: WindowsInput) -> int:
    print(f"Gesture Mouse {__version__}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"MediaPipe: {mp.__version__}")
    print(f"OpenCV: {cv2.__version__}")
    print(f"Screen: {controller.screen_size[0]}x{controller.screen_size[1]}")
    for index, monitor in enumerate(controller.monitors):
        print(
            f"Monitor {index}: {monitor.width}x{monitor.height} "
            f"at ({monitor.x},{monitor.y}) primary={monitor.primary}"
        )
    print(f"Config: {DEFAULT_CONFIG}")
    print(f"Model: {MODEL_PATH} ({MODEL_PATH.stat().st_size:,} bytes)")
    started = time.perf_counter()
    with build_landmarker(config):
        pass
    print(f"Model initialization: {(time.perf_counter() - started) * 1000:.0f} ms")
    print("Diagnosis: OK")
    return 0


def camera_test(config: AppConfig, camera_override: int | None) -> int:
    capture = open_camera(config, camera_override)
    try:
        successful = 0
        frame_shape = None
        deadline = time.monotonic() + 5.0
        while successful < 10 and time.monotonic() < deadline:
            ok, frame = capture.read()
            if ok and frame is not None:
                successful += 1
                frame_shape = frame.shape
        if successful < 10 or frame_shape is None:
            raise RuntimeError("攝影機已開啟，但無法穩定取得影像")
        print(
            f"Camera test: OK ({frame_shape[1]}x{frame_shape[0]}, "
            f"{successful} frames)"
        )
        return 0
    finally:
        capture.release()


def perform_event(
    event: GestureEvent,
    controller: WindowsInput,
    navigation_mode: str,
    scroll_wheel_delta: int,
) -> str:
    if event == GestureEvent.LEFT_CLICK:
        controller.left_click()
        return "LEFT CLICK"
    if event == GestureEvent.LEFT_DOWN:
        controller.left_down()
        return "DRAG START"
    if event == GestureEvent.LEFT_UP:
        controller.left_up()
        return "DRAG END"
    if event == GestureEvent.RIGHT_CLICK:
        controller.right_click()
        return "RIGHT CLICK"
    if event == GestureEvent.PREVIOUS:
        controller.navigate("previous", navigation_mode)
        return "PREVIOUS"
    if event == GestureEvent.NEXT:
        controller.navigate("next", navigation_mode)
        return "NEXT"
    if event == GestureEvent.SCROLL_UP:
        controller.scroll("up", scroll_wheel_delta)
        return "SCROLL UP"
    if event == GestureEvent.SCROLL_DOWN:
        controller.scroll("down", scroll_wheel_delta)
        return "SCROLL DOWN"
    return ""


def run(
    config: AppConfig,
    args: argparse.Namespace,
    controller: WindowsInput,
    logger: logging.Logger,
) -> int:
    control_enabled = not args.no_control
    show_preview = config.display.preview and not args.no_preview
    detail_visible = show_preview and config.display.detail_window
    capture = open_camera(config, args.camera)
    screen_width, screen_height = controller.screen_size
    cursor = CursorMapper(screen_width, screen_height, config.cursor)
    gestures = GestureEngine(config.gestures)
    paused = False
    activation_at = time.monotonic() + config.activation_delay_seconds
    latest_action = ""
    latest_action_at = 0.0
    previous_frame_at = time.perf_counter()
    fps = 0.0
    failed_frames = 0
    last_timestamp_ms = 0
    cursor_position: tuple[int, int] | None = None
    detail_monitor = controller.monitor_for_window_title(
        config.display.detail_follow_window_title
    )
    if detail_monitor is None:
        detail_monitor = controller.monitor(config.display.detail_monitor_index)
        detail_monitor_source = (
            f"monitor-index:{config.display.detail_monitor_index}"
        )
    else:
        detail_monitor_source = (
            f"window-title:{config.display.detail_follow_window_title}"
        )
    detail_reposition_frames = 0

    def position_detail_window() -> None:
        detail_width = min(
            config.display.detail_window_width,
            detail_monitor.width,
        )
        detail_height = min(
            config.display.detail_window_height,
            detail_monitor.height,
        )
        cv2.resizeWindow(DETAIL_WINDOW_NAME, detail_width, detail_height)
        cv2.moveWindow(
            DETAIL_WINDOW_NAME,
            detail_monitor.x + detail_monitor.width - detail_width,
            detail_monitor.y,
        )

    def create_detail_window() -> None:
        nonlocal detail_reposition_frames
        cv2.namedWindow(DETAIL_WINDOW_NAME, cv2.WINDOW_NORMAL)
        position_detail_window()
        detail_reposition_frames = 30
        if config.display.detail_always_on_top:
            cv2.setWindowProperty(DETAIL_WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

    if show_preview:
        cv2.namedWindow(CAMERA_WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(CAMERA_WINDOW_NAME, 800, 600)
        if config.display.always_on_top:
            cv2.setWindowProperty(CAMERA_WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
        if detail_visible:
            create_detail_window()
        cv2.moveWindow(CAMERA_WINDOW_NAME, 20, 50)

    logger.info(
        "Started: control=%s scroll_only=%s camera=%s screen=%sx%s "
        "detail_monitor=(%s,%s,%sx%s) source=%s",
        control_enabled,
        config.gestures.scroll_only,
        config.camera.index if args.camera is None else args.camera,
        screen_width,
        screen_height,
        detail_monitor.x,
        detail_monitor.y,
        detail_monitor.width,
        detail_monitor.height,
        detail_monitor_source,
    )

    try:
        with build_landmarker(config) as landmarker:
            while True:
                if controller.escape_pressed():
                    break
                if controller.consume_pause_toggle():
                    paused = not paused
                    controller.release_all()
                    gestures.reset()
                    cursor.reset()
                    latest_action = "PAUSED" if paused else "RESUMED"
                    latest_action_at = time.monotonic()
                if controller.consume_detail_toggle() and show_preview:
                    detail_visible = not detail_visible
                    if detail_visible:
                        create_detail_window()
                    else:
                        cv2.destroyWindow(DETAIL_WINDOW_NAME)

                ok, frame = capture.read()
                if not ok or frame is None:
                    failed_frames += 1
                    if failed_frames >= 30:
                        raise RuntimeError("連續 30 幀無法讀取攝影機影像")
                    continue
                failed_frames = 0
                frame = cv2.flip(frame, 1)
                camera_frame = frame.copy()
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb = np.ascontiguousarray(rgb)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = max(
                    last_timestamp_ms + 1,
                    int(time.perf_counter() * 1000),
                )
                last_timestamp_ms = timestamp_ms
                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                landmarks = result.hand_landmarks[0] if result.hand_landmarks else None
                handedness = ""
                handedness_score = 0.0
                if result.handedness and result.handedness[0]:
                    category = result.handedness[0][0]
                    handedness = category.category_name or category.display_name or ""
                    handedness_score = float(category.score or 0.0)
                now = time.monotonic()
                metrics = analyze_landmarks(landmarks) if landmarks is not None else None

                if landmarks is None:
                    gesture_frame = gestures.no_hand()
                    cursor.reset()
                    cursor_position = None
                elif paused:
                    gesture_frame = None
                else:
                    gesture_frame = gestures.update(metrics, now)

                if gesture_frame is not None:
                    if (
                        gesture_frame.cursor_active
                        and gesture_frame.control_point is not None
                        and not config.gestures.scroll_only
                    ):
                        cursor_position = cursor.map(gesture_frame.control_point)
                        if control_enabled and now >= activation_at:
                            controller.move(*cursor_position)
                    if control_enabled and now >= activation_at:
                        for event in gesture_frame.events:
                            if (
                                config.gestures.scroll_only
                                and event
                                not in {
                                    GestureEvent.SCROLL_UP,
                                    GestureEvent.SCROLL_DOWN,
                                }
                            ):
                                continue
                            action = perform_event(
                                event,
                                controller,
                                config.navigation_mode,
                                (
                                    gesture_frame.scroll_wheel_delta
                                    or config.gestures.scroll_wheel_delta
                                ),
                            )
                            if action:
                                latest_action = action
                                latest_action_at = now
                                logger.info("Gesture action: %s", action)
                    elif gesture_frame.events:
                        latest_action = gesture_frame.events[-1].value.upper()
                        latest_action_at = now

                current_frame_at = time.perf_counter()
                instant_fps = 1.0 / max(current_frame_at - previous_frame_at, 1e-6)
                fps = instant_fps if fps == 0 else fps * 0.90 + instant_fps * 0.10
                previous_frame_at = current_frame_at

                if show_preview:
                    draw_roi(frame, config.cursor)
                    if landmarks is not None and config.display.show_landmarks:
                        draw_landmarks(frame, landmarks)
                    if now - latest_action_at > 0.8:
                        latest_action = ""
                    if paused:
                        status = "PAUSED"
                    elif now < activation_at and control_enabled:
                        status = f"STARTING IN {max(0, activation_at - now):.1f}s"
                    elif gesture_frame is None:
                        status = "PAUSED"
                    else:
                        status = gesture_frame.mode
                    draw_status(
                        frame,
                        status,
                        fps,
                        paused,
                        control_enabled,
                        latest_action,
                    )
                    cv2.imshow(CAMERA_WINDOW_NAME, frame)
                    if detail_visible:
                        detail_frame = create_tracking_view(
                            camera_frame,
                            landmarks,
                            metrics,
                            gesture_frame,
                            handedness=handedness,
                            handedness_score=handedness_score,
                            cursor_position=cursor_position,
                            latest_action=latest_action,
                            fps=fps,
                            pinch_threshold=config.gestures.pinch_threshold,
                            paused=paused,
                            control_enabled=control_enabled,
                            show_landmark_numbers=(
                                config.display.show_landmark_numbers
                            ),
                        )
                        cv2.imshow(DETAIL_WINDOW_NAME, detail_frame)
                        if detail_reposition_frames > 0:
                            position_detail_window()
                            detail_reposition_frames -= 1
                    key = cv2.waitKey(1) & 0xFF
                    if key in (27, ord("q"), ord("Q")):
                        break
                    if key in (ord("p"), ord("P")):
                        paused = not paused
                        controller.release_all()
                        gestures.reset()
                        cursor.reset()
                    if key in (ord("d"), ord("D")):
                        detail_visible = not detail_visible
                        if detail_visible:
                            create_detail_window()
                        else:
                            cv2.destroyWindow(DETAIL_WINDOW_NAME)

        return 0
    finally:
        controller.release_all()
        capture.release()
        cv2.destroyAllWindows()
        logger.info("Stopped")


def main() -> int:
    args = parse_args()
    logger = configure_logging()
    try:
        config = load_config(args.config.resolve())
        controller = WindowsInput()
        if args.diagnose:
            return diagnose(config, controller)
        if args.camera_test:
            return camera_test(config, args.camera)
        return run(config, args, controller, logger)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        logger.exception("Fatal error")
        print(f"\n錯誤：{exc}", file=sys.stderr)
        print(f"詳細記錄：{PROJECT_ROOT / 'logs' / 'gesture_mouse.log'}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
