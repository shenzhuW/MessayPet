# core/window_interaction/edge_crawler.py
"""
边缘爬行模块 - 桌面宠物沿窗口边缘爬行的核心逻辑
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Callable, Optional, Tuple
import time

from PySide6.QtCore import QTimer


class Edge(IntEnum):
    """爬行边缘定义"""
    TOP = 0
    RIGHT = 1
    BOTTOM = 2
    LEFT = 3


class Direction(IntEnum):
    """爬行方向"""
    CLOCKWISE = 1
    COUNTER_CLOCKWISE = -1


class EdgeCrawlerState(IntEnum):
    """边缘爬行状态"""
    IDLE = 0
    MOVING = 1
    CORNER_PAUSE = 2


@dataclass
class CrawlState:
    """爬行状态"""
    edge: Edge = Edge.TOP
    offset: float = 0.0
    direction: Direction = Direction.CLOCKWISE
    speed: float = 2.0
    corner_pause_ms: int = 200
    _corner_timer: float = 0.0


class EdgeTransitionState(IntEnum):
    """边过渡状态"""
    MOVING = 0
    CORNER_PAUSE = 1
    STAYING_AT_CORNER = 2


class EdgeTransitionManager:
    """边过渡管理器 - 保证宠物平滑转弯"""

    def __init__(self):
        self._state: str = "moving"  # "moving" | "corner_pause" | "staying_at_corner"
        self._corner_start_pos: Optional[Tuple[int, int]] = None
        self._last_edge: Optional[Edge] = None

    def on_edge_reached(self, state: CrawlState) -> bool:
        """
        当一条边爬行完成时调用，返回是否开始角点暂停

        返回 True 表示可以开始角点暂停
        """
        if self._state == "moving":
            self._corner_start_pos = None
            self._state = "corner_pause"
            state._corner_timer = 0.0
            return True
        return False

    def update_corner_timer(self, state: CrawlState, dt_ms: float) -> bool:
        """
        更新角点暂停计时器

        返回 True 表示暂停结束，可以过渡
        """
        if self._state == "corner_pause":
            state._corner_timer += dt_ms
            if state._corner_timer >= state.corner_pause_ms:
                return True
        return False

    def can_start_moving(self) -> bool:
        """检查是否可以开始移动"""
        return self._state == "staying_at_corner"

    def start_moving(self):
        """开始移动"""
        self._state = "moving"

    def perform_transition(self, state: CrawlState, window: Tuple[int, int, int, int],
                           pet_size: Tuple[int, int]) -> None:
        """
        执行边过渡：切换到下一条边

        核心原则：过渡后 offset = 0（新边起点），位置保持连续
        """
        old_edge = state.edge
        new_edge = self._get_next_edge(state.edge, state.direction)
        self._last_edge = old_edge

        # 计算旧边终点的角点位置
        corner_pos = calculate_pet_position(window, pet_size, old_edge, state.offset)

        # 计算新边的 offset，使 offset=0 时位置等于 corner_pos
        x, y, w, h = window

        if new_edge == Edge.TOP:
            # (x + offset, y - ph) = corner_pos -> offset = corner_pos[0] - x
            state.offset = max(0.0, corner_pos[0] - x)
        elif new_edge == Edge.RIGHT:
            # (x + w - pw, y - ph + offset) = corner_pos -> offset = corner_pos[1] - y + ph
            state.offset = max(0.0, corner_pos[1] - y + pet_size[1])
        elif new_edge == Edge.BOTTOM:
            # (x + w - pw - offset, y + h - ph) = corner_pos -> offset = x + w - pw - corner_pos[0]
            state.offset = max(0.0, x + w - pet_size[0] - corner_pos[0])
        elif new_edge == Edge.LEFT:
            # (x, y + h - ph - offset) = corner_pos -> offset = y + h - ph - corner_pos[1]
            state.offset = max(0.0, y + h - pet_size[1] - corner_pos[1])

        state.edge = new_edge
        self._state = "staying_at_corner"

    def _get_next_edge(self, current: Edge, direction: Direction) -> Edge:
        """获取下一条边"""
        next_val = int(current) + direction.value
        return Edge(((next_val % 4) + 4) % 4)

    def reset(self):
        """重置过渡状态"""
        self._state = "moving"
        self._corner_start_pos = None
        self._last_edge = None

    @property
    def current_state(self) -> str:
        """获取当前状态"""
        return self._state


def calculate_pet_position(window: Tuple[int, int, int, int],
                           pet_size: Tuple[int, int],
                           edge: Edge,
                           offset: float) -> Tuple[int, int]:
    """
    计算宠物在指定边缘的绝对屏幕坐标

    角点循环：右上角 -> 右下角 -> 左下角 -> 左上角 -> 右上角

    统一锚点：宠物左上角在角点外侧
    - TOP offset=0:     (x, y-ph)
    - TOP offset=max:   (x+w-pw, y-ph)
    - RIGHT offset=0:   (x+w-pw, y-ph)      <- 右上角
    - RIGHT offset=max: (x+w-pw, y+h-ph)    <- 右下角
    - BOTTOM offset=0:  (x+w-pw, y+h-ph)    <- 右下角
    - BOTTOM offset=max:(x, y+h-ph)         <- 左下角
    - LEFT offset=0:    (x, y+h-ph)         <- 左下角
    - LEFT offset=max:  (x, y-ph)           <- 左上角
    """
    pw, ph = pet_size
    x, y, w, h = window

    if edge == Edge.TOP:
        # offset: 0 -> w-pw
        return (x + int(offset), y - ph)

    elif edge == Edge.RIGHT:
        # offset: 0 -> h-ph，位置从 (x+w-pw, y-ph) 到 (x+w-pw, y+h-ph)
        return (x + w - pw, y - ph + int(offset))

    elif edge == Edge.BOTTOM:
        # offset: 0 -> w-pw，位置从 (x+w-pw, y+h-ph) 到 (x, y+h-ph)
        return (x + w - pw - int(offset), y + h - ph)

    elif edge == Edge.LEFT:
        # offset: 0 -> h-ph，位置从 (x, y+h-ph) 到 (x, y-ph)
        return (x, y + h - ph - int(offset))

    return (x, y)


def get_edge_max_offset(window: Tuple[int, int, int, int],
                        pet_size: Tuple[int, int],
                        edge: Edge) -> float:
    """
    获取给定边缘的最大偏移量

    核心原则：边缘首尾相连
    - TOP offset=0 到 w-pw: 宠物从左上角外侧到右上角外侧
    - RIGHT offset=0 到 h: 宠物从右上角外侧到右下角外侧
    - BOTTOM offset=0 到 w-pw: 宠物从右下角外侧到左下角外侧
    - LEFT offset=0 到 h: 宠物从左下角外侧到左上角外侧
    """
    w, h = window[2], window[3]

    if edge == Edge.TOP:
        return max(w - pet_size[0], 0)
    elif edge == Edge.RIGHT:
        return max(h, 0)  # 用 h 而不是 h-ph
    elif edge == Edge.BOTTOM:
        return max(w - pet_size[0], 0)
    elif edge == Edge.LEFT:
        return max(h, 0)  # 用 h 而不是 h-ph
    return 0.0


class EdgeCrawler:
    """边缘爬行器 - 管理宠物沿窗口边缘爬行的核心逻辑"""

    SPEED_MAP = {"slow": 1.0, "medium": 2.0, "fast": 4.0}

    def __init__(self, pet_size: Tuple[int, int] = (64, 64)):
        self.pet_size = pet_size

        # 爬行状态
        self._state = EdgeCrawlerState.IDLE
        self._crawl = CrawlState()

        # 过渡管理器
        self._transition = EdgeTransitionManager()

        # 回调
        self._position_callback: Optional[Callable] = None

        # 宠物位置
        self._pet_x: int = 0
        self._pet_y: int = 0
        self._manual_move_pending: bool = False

        # 定时器
        self._timer: Optional[QTimer] = None

        # 最后更新时间（用于 dt 计算）
        self._last_update_time: float = time.time()

        # 暂停标志
        self._paused: bool = False

    def set_config(self, direction: str = "clockwise", speed: str = "medium",
                   corner_pause_ms: int = 200):
        """设置跟随配置"""
        self._crawl.direction = Direction.CLOCKWISE if direction == "clockwise" else Direction.COUNTER_CLOCKWISE
        self._crawl.speed = self.SPEED_MAP.get(speed, 2.0)
        self._crawl.corner_pause_ms = corner_pause_ms

    def set_pet_position(self, x: int, y: int):
        """更新宠物位置（手动拖拽时调用）"""
        self._pet_x = x
        self._pet_y = y
        self._manual_move_pending = True

    def set_position_callback(self, callback: Callable):
        """设置位置回调"""
        self._position_callback = callback

    def start(self, window: Tuple[int, int, int, int]):
        """开始跟踪"""
        self._state = EdgeCrawlerState.MOVING
        self._transition.reset()
        self._last_update_time = time.time()
        self._paused = False

        self._timer = QTimer()
        self._timer.timeout.connect(lambda: self.update(window))
        self._timer.start(16)  # ~60fps

    def update(self, window: Tuple[int, int, int, int], dt: float = None):
        """更新爬行状态"""
        if dt is None:
            current_time = time.time()
            dt = current_time - self._last_update_time
            self._last_update_time = current_time

        if self._paused:
            return

        rect = window

        # 处理手动移动 - 宠物被拖拽后找到最近的边
        if self._manual_move_pending:
            self._manual_move_pending = False
            self._find_nearest_edge(rect)
            self._state = EdgeCrawlerState.MOVING

        # 根据过渡状态更新
        if self._transition.current_state == "staying_at_corner":
            # 刚完成边过渡，在角点停留一帧后开始移动
            self._transition.start_moving()

        elif self._state == EdgeCrawlerState.CORNER_PAUSE:
            dt_ms = dt * 1000
            if self._transition.update_corner_timer(self._crawl, dt_ms):
                # 暂停结束，执行边过渡（保持角点位置）
                self._transition.perform_transition(self._crawl, rect, self.pet_size)
                # 进入"在角点停留"状态，下一帧开始沿新边移动

        elif self._state == EdgeCrawlerState.MOVING:
            # 计算最大偏移量
            max_offset = get_edge_max_offset(rect, self.pet_size, self._crawl.edge)

            # 边界检查：如果窗口太小，跳过该边
            if max_offset < 1:
                self._transition.perform_transition(self._crawl, rect, self.pet_size)
                self._crawl.offset = 0.0
            else:
                # 递增偏移量
                step = self._crawl.speed * dt * 60  # 归一化到60fps
                self._crawl.offset += step

                # 检查是否到达边界
                if self._crawl.offset >= max_offset:
                    self._crawl.offset = max_offset
                    if self._transition.on_edge_reached(self._crawl):
                        self._state = EdgeCrawlerState.CORNER_PAUSE

        # 计算并应用位置
        pos = calculate_pet_position(rect, self.pet_size, self._crawl.edge, self._crawl.offset)

        # 严格边界检查：确保宠物不会超出窗口区域
        pw, ph = self.pet_size
        win_x, win_y, win_w, win_h = rect

        # 计算宠物在当前边缘的允许范围
        if self._crawl.edge == Edge.TOP:
            # 水平边：宠物 X 范围 [win_x, win_x + win_w - pw]
            max_x = win_x + win_w - pw
            pos = (min(pos[0], max_x), pos[1])
        elif self._crawl.edge == Edge.BOTTOM:
            # 水平边：宠物 X 范围 [win_x, win_x + win_w - pw]
            max_x = win_x + win_w - pw
            pos = (max(win_x, pos[0]), pos[1])
        elif self._crawl.edge == Edge.RIGHT:
            # 垂直边：宠物 Y 范围 [win_y, win_y + win_h - ph]
            max_y = win_y + win_h - ph
            pos = (pos[0], min(pos[1], max_y))
        elif self._crawl.edge == Edge.LEFT:
            # 垂直边：宠物 Y 范围 [win_y, win_y + win_h - ph]
            max_y = win_y + win_h - ph
            pos = (pos[0], max(win_y, pos[1]))

        # 屏幕边界检查
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.geometry()
            # 限制在屏幕范围内
            x = max(0, min(pos[0], screen_rect.width() - pw))
            y = max(0, min(pos[1], screen_rect.height() - ph))
            pos = (x, y)

        if self._position_callback:
            self._position_callback(pos[0], pos[1])

        return pos

    def pause(self):
        """暂停爬行"""
        self._paused = True

    def resume(self):
        """恢复爬行"""
        self._paused = False
        self._manual_move_pending = True

    def stop(self):
        """停止爬行"""
        self._state = EdgeCrawlerState.IDLE
        if self._timer:
            self._timer.stop()
            self._timer = None

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._timer is not None and self._timer.isActive()

    def find_nearest_edge(self, rect: Tuple[int, int, int, int]) -> Tuple[Edge, float]:
        """
        找到距离宠物当前位置最近的边缘

        返回 (edge, offset) 元组
        """
        self._find_nearest_edge(rect)
        return (self._crawl.edge, self._crawl.offset)

    def _find_nearest_edge(self, rect: Tuple[int, int, int, int]):
        """
        找到距离宠物当前位置最近的边缘，并设置相应的边和偏移量
        """
        pw, ph = self.pet_size
        x, y, w, h = rect

        # 宠物中心点
        pet_cx = self._pet_x + pw // 2
        pet_cy = self._pet_y + ph // 2

        # 计算到各边缘的距离（宠物边缘与窗口边缘的垂直/水平距离）
        dist_top = abs((pet_cy + ph // 2) - y) if pet_cy < y else abs(pet_cy - y)
        dist_bottom = abs((pet_cy - ph // 2) - (y + h)) if pet_cy > y + h else abs(pet_cy - (y + h))
        dist_left = abs((pet_cx + pw // 2) - x) if pet_cx < x else abs(pet_cx - x)
        dist_right = abs((pet_cx - pw // 2) - (x + w)) if pet_cx > x + w else abs(pet_cx - (x + w))

        # 容差范围
        margin = 30
        max_offset = get_edge_max_offset(rect, self.pet_size, Edge.TOP)

        # 判断宠物在哪个边缘附近
        if dist_top <= margin and x <= pet_cx <= x + w:
            # 顶部边缘上方
            self._crawl.edge = Edge.TOP
            self._crawl.offset = max(0, min(pet_cx - x, max_offset))
        elif dist_bottom <= margin and x <= pet_cx <= x + w:
            # 底部边缘下方
            self._crawl.edge = Edge.BOTTOM
            self._crawl.offset = max(0, min(pet_cx - x, max_offset))
        elif dist_left <= margin and y <= pet_cy <= y + h:
            # 左侧边缘左侧
            self._crawl.edge = Edge.LEFT
            max_offset = get_edge_max_offset(rect, self.pet_size, Edge.LEFT)
            self._crawl.offset = max(0, min(pet_cy - y, max_offset))
        elif dist_right <= margin and y <= pet_cy <= y + h:
            # 右侧边缘右侧
            self._crawl.edge = Edge.RIGHT
            max_offset = get_edge_max_offset(rect, self.pet_size, Edge.RIGHT)
            self._crawl.offset = max(0, min(pet_cy - y, max_offset))
        else:
            # 不在任何边缘附近，默认从顶部开始
            self._crawl.edge = Edge.TOP
            self._crawl.offset = 0.0

    def is_at_corner(self) -> bool:
        """检查是否在角点位置"""
        return self._transition.current_state in ("corner_pause", "staying_at_corner")

    @property
    def current_state(self) -> EdgeCrawlerState:
        """获取当前爬行状态"""
        return self._state

    @property
    def current_edge(self) -> Edge:
        """获取当前所在边缘"""
        return self._crawl.edge

    @property
    def current_offset(self) -> float:
        """获取当前偏移量"""
        return self._crawl.offset