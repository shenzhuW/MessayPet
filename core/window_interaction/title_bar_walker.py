from enum import IntEnum
from typing import Optional, Tuple, Callable
from .window_info_provider import WindowInfoProvider


class TitleBarState(IntEnum):
    """标题栏行走状态"""
    IDLE = 0
    WALKING = 1
    CORNER_PAUSE = 2


class TitleBarWalker:
    """标题栏行走器"""

    def __init__(self, window_provider: WindowInfoProvider, pet_size: Tuple[int, int] = (64, 64)):
        self._provider = window_provider
        self.pet_size = pet_size
        self._state = TitleBarState.IDLE
        self._offset = 0.0
        self._direction = 1  # 1 = 右, -1 = 左
        self._current_hwnd: Optional[int] = None
        self._on_position_update: Optional[Callable] = None
        self._corner_pause_ms = 200
        self._corner_timer = 0.0

    def set_position_callback(self, callback: Callable[[int, int], None]):
        self._on_position_update = callback

    def start(self, hwnd: int):
        """开始标题栏行走"""
        title_bar_rect = self._provider.get_title_bar_rect(hwnd)
        if not title_bar_rect:
            return False

        self._current_hwnd = hwnd
        self._offset = 0.0
        self._direction = 1
        self._state = TitleBarState.WALKING
        return True

    def stop(self):
        """停止行走"""
        self._state = TitleBarState.IDLE
        self._current_hwnd = None

    def pause(self):
        self._state = TitleBarState.IDLE

    def resume(self):
        if self._current_hwnd:
            self._state = TitleBarState.WALKING

    def update(self, dt: float):
        """更新行走状态"""
        if self._state == TitleBarState.IDLE:
            return None

        if self._state == TitleBarState.CORNER_PAUSE:
            self._corner_timer += dt * 1000
            if self._corner_timer >= self._corner_pause_ms:
                self._state = TitleBarState.WALKING
                self._corner_timer = 0.0
                self._direction *= -1
            return None

        if not self._current_hwnd:
            return None

        title_bar_rect = self._provider.get_title_bar_rect(self._current_hwnd)
        if not title_bar_rect:
            return None

        tb_x, tb_y, tb_w, tb_h = title_bar_rect
        pw, ph = self.pet_size

        max_offset = max(tb_w - pw, 0)
        speed = 1.0

        self._offset += speed * self._direction * dt * 60

        if self._offset >= max_offset:
            self._offset = max_offset
            self._state = TitleBarState.CORNER_PAUSE
        elif self._offset <= 0:
            self._offset = 0
            self._state = TitleBarState.CORNER_PAUSE

        pos = (int(tb_x + self._offset), int(tb_y - ph))

        if self._on_position_update:
            self._on_position_update(pos[0], pos[1])

        return pos

    def jump_to_new_window(self, hwnd: int):
        """跳转到新窗口的标题栏"""
        self._current_hwnd = hwnd
        self._offset = 0.0
        self._direction = 1
        self._state = TitleBarState.WALKING