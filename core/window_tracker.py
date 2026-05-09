# core/window_tracker.py
"""
窗口追踪模块 - 追踪前台窗口位置

此模块保留向后兼容接口，内部使用 EdgeCrawler 实现核心逻辑。
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Callable, Optional, List, Tuple
import time

from PySide6.QtCore import QTimer

from core.window_interaction.window_info_provider import WindowInfoProvider, WindowInfo
from core.window_interaction.edge_crawler import (
    Edge, Direction, CrawlState,
    calculate_pet_position, get_edge_max_offset, EdgeCrawler
)

try:
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class PetState(IntEnum):
    """宠物状态"""
    IDLE = 0
    CRAWLING = 1
    CORNER_PAUSE = 2
    MANUAL = 3


class WindowTracker:
    """窗口跟踪器 - 管理宠物沿窗口边缘爬行

    此类的接口保持向后兼容，内部委托给 EdgeCrawler 处理核心爬行逻辑。
    """

    def __init__(self, pet_size: Tuple[int, int] = (64, 64), event_bus=None):
        self.pet_size = pet_size
        self.event_bus = event_bus

        # 创建边缘爬行器
        self._crawler = EdgeCrawler(pet_size)

        # 配置
        self._enabled = False
        self._speed_mode = "medium"

        # 回调（保留用于外部兼容性）
        self._target_callback: Optional[Callable] = None

        # 窗口状态
        self._last_hwnd: Optional[int] = None
        self._last_window_rect: Optional[Tuple[int, int, int, int]] = None
        self._last_focused_hwnd: Optional[int] = None
        self._window_stable_time: float = 0.0
        self._stable_threshold = 3.0  # 窗口稳定3秒后暂停

        # 状态
        self._state = PetState.IDLE
        self._paused = False

        # 定时器
        self._timer: Optional[QTimer] = None

        # 最后更新时间（用于 dt 计算）
        self._last_update_time: float = time.time()

    def set_config(self, direction: str = "clockwise", speed: str = "medium",
                   corner_pause_ms: int = 200):
        """设置跟随配置"""
        self._crawler.set_config(direction, speed, corner_pause_ms)

    def set_pet_position(self, x: int, y: int):
        """更新宠物位置（手动拖拽时调用）"""
        self._crawler.set_pet_position(x, y)
        self._state = PetState.MANUAL

    def pause(self):
        """暂停跟踪（拖拽开始时调用）"""
        self._paused = True
        self._crawler.pause()
        self._state = PetState.MANUAL

    def resume(self):
        """恢复跟踪（拖拽结束时调用）"""
        self._paused = False
        self._crawler.resume()
        self._state = PetState.CRAWLING

    def start_tracking(self, callback: Callable):
        """开始跟踪"""
        self._enabled = True
        self._target_callback = callback
        self._state = PetState.CRAWLING

        # 设置爬行器回调
        self._crawler.set_position_callback(callback)

        # 获取前台窗口并启动
        fg = self.get_foreground_window()
        if fg:
            rect = (fg.x, fg.y, fg.width, fg.height)
            self._crawler.start(rect)

        self._last_update_time = time.time()

    def stop_tracking(self):
        """停止跟踪"""
        self._enabled = False
        self._target_callback = None
        self._state = PetState.IDLE
        self._crawler.stop()
        if self._timer:
            self._timer.stop()
            self._timer = None

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._enabled and self._crawler.is_running()

    def get_foreground_window(self) -> Optional[WindowInfo]:
        """获取前台窗口信息"""
        return WindowInfoProvider.get_foreground_window()

    def _reset_to_top_edge(self):
        """重置到顶部边缘"""
        self._crawler._crawl.edge = Edge.TOP
        self._crawler._crawl.offset = 0.0
        self._crawler._transition.reset()

    def get_all_windows(self) -> List[WindowInfo]:
        """获取所有可见窗口"""
        return WindowInfoProvider.get_all_windows()