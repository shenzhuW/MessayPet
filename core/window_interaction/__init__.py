# core/window_interaction/__init__.py
"""窗口交互模块 - Shimeji 风格窗口交互功能"""

from .window_info_provider import WindowInfoProvider
from .behavior_scheduler import BehaviorScheduler
from .jump_target_selector import JumpTargetSelector
from .react_engine import ReactEngine
from .edge_crawler import (
    EdgeCrawler,
    Edge,
    Direction,
    EdgeCrawlerState,
    CrawlState,
    EdgeTransitionState,
    EdgeTransitionManager,
    calculate_pet_position,
    get_edge_max_offset,
)
from .title_bar_walker import TitleBarWalker
from .taskbar_walker import TaskbarWalker
from .window_interaction_manager import WindowInteractionManager

__all__ = [
    "WindowInfoProvider",
    "BehaviorScheduler",
    "JumpTargetSelector",
    "ReactEngine",
    "EdgeCrawler",
    "Edge",
    "Direction",
    "EdgeCrawlerState",
    "CrawlState",
    "EdgeTransitionState",
    "EdgeTransitionManager",
    "calculate_pet_position",
    "get_edge_max_offset",
    "TitleBarWalker",
    "TaskbarWalker",
    "WindowInteractionManager",
]