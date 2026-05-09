from enum import IntEnum
from dataclasses import dataclass
import random
import time


class BehaviorType(IntEnum):
    """行为类型"""
    IDLE = 0
    CRAWLING = 1
    JUMPING = 2
    TITLE_BAR = 3
    TASKBAR = 4
    REACTING = 5


@dataclass
class BehaviorState:
    """行为状态"""
    current: BehaviorType = BehaviorType.IDLE
    start_time: float = 0.0
    paused: bool = False


class BehaviorScheduler:
    """行为调度器"""

    PRIORITY = {
        BehaviorType.REACTING: 5,  # 反应最高
        BehaviorType.JUMPING: 4,
        BehaviorType.TITLE_BAR: 3,
        BehaviorType.TASKBAR: 2,
        BehaviorType.CRAWLING: 1,
        BehaviorType.IDLE: 0,
    }

    JUMP_PROBABILITY_PER_MINUTE = 0.1
    JUMP_CHECK_INTERVAL = 60.0  # 秒

    def __init__(self):
        self._state = BehaviorState()
        self._last_jump_check = time.time()
        self._jump_countdown = self.JUMP_CHECK_INTERVAL

    def get_current_behavior(self) -> BehaviorType:
        """获取当前行为"""
        return self._state.current

    def can_transition_to(self, new_behavior: BehaviorType) -> bool:
        """检查是否可以转换到新行为（基于优先级）"""
        current_priority = self.PRIORITY.get(self._state.current, 0)
        new_priority = self.PRIORITY.get(new_behavior, 0)
        return new_priority > current_priority

    def set_behavior(self, behavior: BehaviorType):
        """设置当前行为"""
        if behavior != self._state.current:
            self._state.current = behavior
            self._state.start_time = time.time()

    def should_jump(self) -> bool:
        """检查是否应该跳转（每分钟 10% 几率）"""
        now = time.time()
        if now - self._last_jump_check >= self._jump_countdown:
            self._last_jump_check = now
            self._jump_countdown = self.JUMP_CHECK_INTERVAL
            return random.random() < self.JUMP_PROBABILITY_PER_MINUTE
        return False

    def should_jump_on_corner(self) -> bool:
        """角点暂停时是否跳转（50% 几率）"""
        return random.random() < 0.5

    def on_window_changed(self):
        """窗口切换时调用"""
        self._last_jump_check = time.time()
        self._jump_countdown = self.JUMP_CHECK_INTERVAL * random.uniform(0.5, 1.5)

    def pause(self):
        """暂停"""
        self._state.paused = True

    def resume(self):
        """恢复"""
        self._state.paused = False

    def reset(self):
        """重置"""
        self._state.current = BehaviorType.IDLE
        self._state.paused = False
        self._last_jump_check = time.time()
        self._jump_countdown = self.JUMP_CHECK_INTERVAL