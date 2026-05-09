# core/window_interaction/window_interaction_manager.py
"""窗口交互管理器 - 统一协调所有行为模块"""
import time
from typing import Optional, Callable, Tuple
from PySide6.QtCore import QTimer

from .window_info_provider import WindowInfoProvider, WindowInfo
from .behavior_scheduler import BehaviorScheduler, BehaviorType
from .jump_target_selector import JumpTargetSelector
from .react_engine import ReactEngine, Reaction
from .edge_crawler import EdgeCrawler
from .title_bar_walker import TitleBarWalker
from .taskbar_walker import TaskbarWalker


class WindowInteractionManager:
    """窗口交互管理器 - 统一协调所有行为模块"""

    def __init__(self, pet_size: Tuple[int, int] = (64, 64), event_bus=None):
        self.pet_size = pet_size
        self.event_bus = event_bus

        self._window_provider = WindowInfoProvider()
        self._scheduler = BehaviorScheduler()
        self._jump_selector = JumpTargetSelector(self._window_provider)
        self._react_engine = ReactEngine()

        self._edge_crawler = EdgeCrawler(pet_size)
        self._title_bar_walker = TitleBarWalker(self._window_provider, pet_size)
        self._taskbar_walker = TaskbarWalker(self._window_provider, pet_size)

        self._timer: Optional[QTimer] = None
        self._last_update_time = time.time()
        self._last_hwnd: Optional[int] = None

        self._target_callback: Optional[Callable] = None
        self._paused = False
        self._enabled = False

        self._pet_x = 0
        self._pet_y = 0
        self._manual_move_pending = False

        self._setup_callbacks()

    def _setup_callbacks(self):
        """设置内部回调"""
        self._edge_crawler.set_position_callback(self._on_position_update)
        self._title_bar_walker.set_position_callback(self._on_position_update)
        self._taskbar_walker.set_position_callback(self._on_position_update)

    def set_config(self, direction: str = "clockwise", speed: str = "medium",
                   corner_pause_ms: int = 200):
        """设置配置"""
        self._edge_crawler.set_config(direction, speed, corner_pause_ms)
        self._title_bar_walker._corner_pause_ms = corner_pause_ms
        self._taskbar_walker._corner_pause_ms = corner_pause_ms

    def set_reaction_callback(self, callback: Callable[[Reaction], None]):
        """设置反应回调"""
        self._react_engine.set_reaction_callback(callback)

    def set_pet_position(self, x: int, y: int):
        """更新宠物位置（手动拖拽时调用）"""
        self._pet_x = x
        self._pet_y = y
        self._manual_move_pending = True
        self._edge_crawler.set_pet_position(x, y)

    def set_position_callback(self, callback: Callable[[int, int], None]):
        """设置位置更新回调"""
        self._target_callback = callback

    def pause(self):
        """暂停跟踪"""
        self._paused = True
        self._scheduler.pause()
        self._edge_crawler.pause()
        self._title_bar_walker.pause()
        self._taskbar_walker.pause()

    def resume(self):
        """恢复跟踪"""
        self._paused = False
        self._manual_move_pending = True
        self._scheduler.resume()
        self._scheduler.set_behavior(BehaviorType.CRAWLING)

    def start(self):
        """开始跟踪"""
        self._enabled = True
        self._scheduler.set_behavior(BehaviorType.CRAWLING)

        # 初始化 EdgeCrawler 状态（不启动它自己的 timer，由 WindowInteractionManager 控制）
        from .edge_crawler import EdgeCrawlerState
        self._edge_crawler._state = EdgeCrawlerState.MOVING
        self._edge_crawler._transition.reset()

        self._timer = QTimer()
        self._timer.timeout.connect(self._update_loop)
        self._timer.start(16)

        self._last_update_time = time.time()

    def stop(self):
        """停止跟踪"""
        self._enabled = False
        if self._timer:
            self._timer.stop()
            self._timer = None

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._enabled and self._timer is not None and self._timer.isActive()

    def get_foreground_window(self) -> Optional[WindowInfo]:
        """获取前台窗口信息"""
        return self._window_provider.get_foreground_window()

    def get_all_windows(self) -> list:
        """获取所有窗口"""
        return self._window_provider.get_all_windows()

    def _on_position_update(self, x: int, y: int):
        """内部位置更新回调"""
        if self._target_callback:
            self._target_callback(x, y)

    def _update_loop(self):
        """更新循环"""
        current_time = time.time()
        dt = current_time - self._last_update_time
        self._last_update_time = current_time

        if not self._enabled or self._paused:
            return

        fg = self._window_provider.get_foreground_window()
        if not fg:
            return

        rect = (fg.x, fg.y, fg.width, fg.height)

        if self._last_hwnd != fg.hwnd:
            self._on_window_changed(self._last_hwnd, fg.hwnd)
            self._last_hwnd = fg.hwnd

        if self._manual_move_pending:
            self._manual_move_pending = False
            self._edge_crawler.find_nearest_edge(rect)
            self._scheduler.set_behavior(BehaviorType.CRAWLING)

        current_behavior = self._scheduler.get_current_behavior()

        if current_behavior == BehaviorType.CRAWLING:
            self._edge_crawler.update(rect, dt)

            if self._edge_crawler.is_at_corner():
                if self._scheduler.should_jump_on_corner():
                    self._try_jump(fg)

        elif current_behavior == BehaviorType.JUMPING:
            pass

        elif current_behavior == BehaviorType.TITLE_BAR:
            self._title_bar_walker.update(dt)

        elif current_behavior == BehaviorType.TASKBAR:
            self._taskbar_walker.update(dt)

        if self._scheduler.should_jump() and current_behavior == BehaviorType.CRAWLING:
            self._try_jump(fg)

    def _on_window_changed(self, old_hwnd: Optional[int], new_hwnd: int):
        """窗口切换处理"""
        self._scheduler.on_window_changed()
        self._react_engine.on_window_changed(old_hwnd or 0, new_hwnd)

        if self.event_bus:
            from core.event_bus import EventType
            fg = self._window_provider.get_foreground_window()
            self.event_bus.publish(EventType.WINDOW_CHANGED, {
                "hwnd": new_hwnd,
                "title": fg.title if fg else ""
            })

        self._last_hwnd = new_hwnd

    def _try_jump(self, current_window: WindowInfo):
        """尝试跳转"""
        target = self._jump_selector.select_target(current_window.hwnd)
        if not target:
            return

        # 随机选择跳转类型（标题栏或任务栏）
        import random
        jump_type = random.randint(0, 1)

        if jump_type == 0:
            self._scheduler.set_behavior(BehaviorType.TITLE_BAR)
            self._title_bar_walker.jump_to_new_window(target.hwnd)
        else:
            self._scheduler.set_behavior(BehaviorType.TASKBAR)
            self._taskbar_walker.start()

            QTimer.singleShot(5000, lambda: self._scheduler.set_behavior(BehaviorType.CRAWLING))