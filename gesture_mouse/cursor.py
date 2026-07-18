from __future__ import annotations

import math

from gesture_mouse.config import CursorConfig
from gesture_mouse.geometry import Point


class CursorMapper:
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        config: CursorConfig,
    ) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.config = config
        self._position: tuple[float, float] | None = None

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def map(self, camera_point: Point) -> tuple[int, int]:
        margin_x = self.config.horizontal_margin
        margin_y = self.config.vertical_margin
        normalized_x = (camera_point[0] - margin_x) / (1.0 - 2.0 * margin_x)
        normalized_y = (camera_point[1] - margin_y) / (1.0 - 2.0 * margin_y)
        target_x = self._clamp(normalized_x, 0.0, 1.0) * (self.screen_width - 1)
        target_y = self._clamp(normalized_y, 0.0, 1.0) * (self.screen_height - 1)

        if self._position is None:
            self._position = target_x, target_y
        else:
            alpha = self.config.smoothing
            current_x, current_y = self._position
            candidate_x = current_x + (target_x - current_x) * alpha
            candidate_y = current_y + (target_y - current_y) * alpha
            if (
                math.hypot(candidate_x - current_x, candidate_y - current_y)
                >= self.config.minimum_move_pixels
            ):
                self._position = candidate_x, candidate_y

        return round(self._position[0]), round(self._position[1])

    def reset(self) -> None:
        self._position = None
