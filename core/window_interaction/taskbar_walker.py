from enum import IntEnum
from typing import Optional, Tuple, Callable
from .window_info_provider import WindowInfoProvider


class TaskbarState(IntEnum):
    """任务栏行走状态"""
    IDLE = 0
    WALKING = 1
    CORNER_PAUSE = 2


class TaskbarWalker:
    """任务栏行走器"""

    def __init__(self, window_provider: WindowInfoProvider, pet_size: Tuple[int, int] = (64, 64)):
        self._provider = window_provider
        self.pet_size = pet_size
        self._state = TaskbarState.IDLE
        self._offset = 0.0
        self._direction = 1
        self._on_position_update: Optional[Callable] = None
        self._corner_pause_ms = 200
        self._corner_timer = 0.0
        self._current_rect: Optional[Tuple[int, int, int, int]] = None

    def set_position_callback(self, callback: Callable[[int, int], None]):
        self._on_position_update = callback

    def start(self):
        """开始任务栏行走"""
        taskbar_rect = self._provider.get_taskbar_rect()
        if not taskbar_rect:
            return False

        self._current_rect = taskbar_rect
        self._offset = 0.0
        self._direction = 1
        self._state = TaskbarState.WALKING
        return True

    def stop(self):
        """停止行走"""
        self._state = TaskbarState.IDLE
        self._current_rect = None

    def pause(self):
        self._state = TaskbarState.IDLE

    def resume(self):
        if self._current_rect:
            self._state = TaskbarState.WALKING

    def update(self, dt: float):
        """更新行走状态"""
        if self._state == TaskbarState.IDLE:
            return None

        if self._state == TaskbarState.CORNER_PAUSE:
            self._corner_timer += dt * 1000
            if self._corner_timer >= self._corner_pause_ms:
                self._state = TaskbarState.WALKING
                self._corner_timer = 0.0
                self._direction *= -1
            return None

        if not self._current_rect:
            return None

        tb_x, tb_y, tb_w, tb_h = self._current_rect
        pw, ph = self.pet_size

        max_offset = max(tb_w - pw, 0)
        speed = 1.5

        self._offset += speed * self._direction * dt * 60

        if self._offset >= max_offset:
            self._offset = max_offset
            self._state = TaskbarState.CORNER_PAUSE
        elif self._offset <= 0:
            self._offset = 0
            self._state = TaskbarState.CORNER_PAUSE

        pos = (int(tb_x + self._offset), int(tb_y - ph))

        if self._on_position_update:
            self._on_position_update(pos[0], pos[1])

        return pos

    def refresh_rect(self):
        """刷新任务栏区域（窗口变化时调用）"""
        self._current_rect = self._provider.get_taskbar_rect()