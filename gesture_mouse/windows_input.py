from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002

VK_ESCAPE = 0x1B
VK_F8 = 0x77
VK_F9 = 0x78
VK_MENU = 0x12
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_PRIOR = 0x21
VK_NEXT = 0x22
MONITOR_DEFAULTTONEAREST = 2


@dataclass(frozen=True)
class MonitorArea:
    x: int
    y: int
    width: int
    height: int
    primary: bool


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class WindowsInput:
    def __init__(self) -> None:
        if not hasattr(ctypes, "windll"):
            raise RuntimeError("此程式僅支援 Windows")
        self._user32 = ctypes.windll.user32
        self._configure_dpi()
        self._configure_signatures()
        self._left_down = False
        self._f8_was_down = False
        self._f9_was_down = False

    def _configure_dpi(self) -> None:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                self._user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass

    def _configure_signatures(self) -> None:
        self._user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        self._user32.SetCursorPos.restype = wintypes.BOOL
        self._user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        self._user32.GetSystemMetrics.restype = ctypes.c_int
        self._user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self._user32.GetAsyncKeyState.restype = ctypes.c_short
        self._user32.mouse_event.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_size_t,
        ]
        self._user32.keybd_event.argtypes = [
            wintypes.BYTE,
            wintypes.BYTE,
            wintypes.DWORD,
            ctypes.c_size_t,
        ]
        self._user32.GetMonitorInfoW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_MonitorInfo),
        ]
        self._user32.GetMonitorInfoW.restype = wintypes.BOOL
        self._user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self._user32.GetWindowTextLengthW.restype = ctypes.c_int
        self._user32.GetWindowTextW.argtypes = [
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        ]
        self._user32.GetWindowTextW.restype = ctypes.c_int
        self._user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self._user32.IsWindowVisible.restype = wintypes.BOOL
        self._user32.MonitorFromWindow.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
        ]
        self._user32.MonitorFromWindow.restype = wintypes.HANDLE

    def _monitor_area(self, monitor_handle) -> MonitorArea | None:
        info = _MonitorInfo()
        info.cbSize = ctypes.sizeof(_MonitorInfo)
        if not self._user32.GetMonitorInfoW(
            monitor_handle,
            ctypes.byref(info),
        ):
            return None
        work = info.rcWork
        return MonitorArea(
            x=work.left,
            y=work.top,
            width=work.right - work.left,
            height=work.bottom - work.top,
            primary=bool(info.dwFlags & 1),
        )

    @property
    def screen_size(self) -> tuple[int, int]:
        return (
            self._user32.GetSystemMetrics(0),
            self._user32.GetSystemMetrics(1),
        )

    @property
    def monitors(self) -> tuple[MonitorArea, ...]:
        monitor_areas: list[MonitorArea] = []
        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HANDLE,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )

        def collect_monitor(
            monitor_handle,
            _device_context,
            _monitor_rect,
            _user_data,
        ):
            area = self._monitor_area(monitor_handle)
            if area is not None:
                monitor_areas.append(area)
            return True

        callback = callback_type(collect_monitor)
        self._user32.EnumDisplayMonitors(None, None, callback, 0)
        if not monitor_areas:
            width, height = self.screen_size
            monitor_areas.append(MonitorArea(0, 0, width, height, True))
        monitor_areas.sort(key=lambda area: (not area.primary, area.x, area.y))
        return tuple(monitor_areas)

    def monitor(self, index: int) -> MonitorArea:
        monitors = self.monitors
        return monitors[index] if index < len(monitors) else monitors[0]

    def monitor_for_window_title(self, title: str) -> MonitorArea | None:
        expected = title.strip().casefold()
        if not expected:
            return None
        matching_windows: list[int] = []
        callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM,
        )

        def collect_window(window_handle, _user_data):
            if not self._user32.IsWindowVisible(window_handle):
                return True
            length = self._user32.GetWindowTextLengthW(window_handle)
            if length <= 0:
                return True
            text = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(window_handle, text, len(text))
            if text.value.strip().casefold() == expected:
                matching_windows.append(window_handle)
            return True

        callback = callback_type(collect_window)
        self._user32.EnumWindows(callback, 0)
        if not matching_windows:
            return None
        monitor_handle = self._user32.MonitorFromWindow(
            matching_windows[0],
            MONITOR_DEFAULTTONEAREST,
        )
        return self._monitor_area(monitor_handle)

    def move(self, x: int, y: int) -> None:
        self._user32.SetCursorPos(x, y)

    def left_click(self) -> None:
        self._user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def left_down(self) -> None:
        if not self._left_down:
            self._user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self._left_down = True

    def left_up(self) -> None:
        if self._left_down:
            self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self._left_down = False

    def right_click(self) -> None:
        self._user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        self._user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def scroll(self, direction: str, wheel_delta: int) -> None:
        delta = wheel_delta * (1 if direction == "up" else -1)
        self._user32.mouse_event(
            MOUSEEVENTF_WHEEL,
            0,
            0,
            delta & 0xFFFFFFFF,
            0,
        )

    def _key(self, virtual_key: int, down: bool) -> None:
        flags = 0 if down else KEYEVENTF_KEYUP
        self._user32.keybd_event(virtual_key, 0, flags, 0)

    def _press_key(self, virtual_key: int) -> None:
        self._key(virtual_key, True)
        self._key(virtual_key, False)

    def _hotkey(self, modifier: int, key: int) -> None:
        self._key(modifier, True)
        self._press_key(key)
        self._key(modifier, False)

    def navigate(self, direction: str, mode: str) -> None:
        if mode == "browser":
            key = VK_LEFT if direction == "previous" else VK_RIGHT
            self._hotkey(VK_MENU, key)
        elif mode == "page":
            self._press_key(VK_PRIOR if direction == "previous" else VK_NEXT)
        else:
            self._press_key(VK_LEFT if direction == "previous" else VK_RIGHT)

    def escape_pressed(self) -> bool:
        return bool(self._user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)

    def consume_pause_toggle(self) -> bool:
        is_down = bool(self._user32.GetAsyncKeyState(VK_F8) & 0x8000)
        toggled = is_down and not self._f8_was_down
        self._f8_was_down = is_down
        return toggled

    def consume_detail_toggle(self) -> bool:
        is_down = bool(self._user32.GetAsyncKeyState(VK_F9) & 0x8000)
        toggled = is_down and not self._f9_was_down
        self._f9_was_down = is_down
        return toggled

    def release_all(self) -> None:
        self.left_up()
