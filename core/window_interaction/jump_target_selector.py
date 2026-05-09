import random
from typing import List, Optional
from .window_info_provider import WindowInfo, WindowInfoProvider


class JumpTargetSelector:
    """跳转目标选择器"""

    FOCUS_WEIGHT = 0.6      # 焦点窗口权重
    RANDOM_WEIGHT = 0.3     # 随机窗口权重
    NEARBY_WEIGHT = 0.1     # 附近窗口权重
    NEARBY_THRESHOLD = 200  # 附近窗口距离阈值（像素）

    def __init__(self, window_provider: WindowInfoProvider):
        self._provider = window_provider

    def select_target(self, current_hwnd: Optional[int] = None) -> Optional[WindowInfo]:
        """选择跳转目标（混合模式）"""
        all_windows = self._provider.get_all_windows()
        if not all_windows:
            return None

        foreground = self._provider.get_foreground_window()

        # 60% 概率跟随焦点窗口
        if random.random() < self.FOCUS_WEIGHT:
            if foreground and self._is_valid_target(foreground, current_hwnd):
                return foreground

        # 30% 概率随机选择
        if random.random() < self.RANDOM_WEIGHT / (1 - self.FOCUS_WEIGHT):
            valid_windows = [w for w in all_windows if self._is_valid_target(w, current_hwnd)]
            if valid_windows:
                return random.choice(valid_windows)

        # 10% 概率选择附近窗口
        if current_hwnd:
            current_rect = self._get_window_rect(current_hwnd)
            if current_rect:
                nearby = [w for w in all_windows
                         if w.hwnd != current_hwnd
                         and self._is_nearby(w.rect, current_rect)
                         and self._is_valid_target(w, current_hwnd)]
                if nearby:
                    return random.choice(nearby)

        # 回退到焦点窗口
        if foreground and self._is_valid_target(foreground, current_hwnd):
            return foreground

        return None

    def _is_valid_target(self, window: WindowInfo, current_hwnd: Optional[int] = None) -> bool:
        """检查窗口是否为有效的跳转目标"""
        if window.hwnd == current_hwnd:
            return False
        if window.width < 100 or window.height < 100:
            return False
        if self._provider.is_fullscreen_window(window.hwnd):
            return False
        return True

    def _is_nearby(self, window_rect: tuple, current_rect: tuple, threshold: int = None) -> bool:
        """判断窗口是否在附近"""
        if threshold is None:
            threshold = self.NEARBY_THRESHOLD

        wx, wy = window_rect[0], window_rect[1]
        cx, cy = current_rect[0], current_rect[1]

        distance = ((wx - cx) ** 2 + (wy - cy) ** 2) ** 0.5
        return distance <= threshold

    def _get_window_rect(self, hwnd: int) -> Optional[tuple]:
        """获取窗口矩形"""
        all_windows = self._provider.get_all_windows()
        for w in all_windows:
            if w.hwnd == hwnd:
                return w.rect
        return None