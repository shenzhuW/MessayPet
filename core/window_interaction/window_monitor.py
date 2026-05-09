from PySide6.QtCore import QTimer
from core.event_bus import EventType
from core.window_interaction.window_info_provider import WindowInfoProvider


class WindowMonitor:
    """窗口变化监控器 - 每 2 秒检查前台窗口变化，发布事件"""

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._last_title = ""
        self._last_hwnd = None
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._check_foreground)
        # 立即获取一次当前窗口
        self._check_foreground()
        self._check_timer.start(2000)

    def _check_foreground(self):
        """检查前台窗口是否变化"""
        info = WindowInfoProvider.get_foreground_window()
        if not info:
            return

        title = info.title
        if title and title != self._last_title:
            self._last_title = title
            self._last_hwnd = info.hwnd
            self.event_bus.publish(EventType.WINDOW_CHANGED, {
                "title": title,
                "hwnd": info.hwnd,
                "rect": info.rect,
                "project_name": info.project_name,
                "display_name": info.display_name,
                "group_key": info.group_key
            })

    def get_current_title(self) -> str:
        """获取当前窗口标题"""
        return self._last_title

    def get_current_hwnd(self):
        return self._last_hwnd

    def stop(self):
        self._check_timer.stop()