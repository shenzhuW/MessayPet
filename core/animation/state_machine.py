from typing import Callable, List, Set


class AnimationStateMachine:
    """动画状态机 - 动态状态，状态名直接使用动作名称"""

    def __init__(self, initial_state: str = "idle"):
        self.current_state = initial_state
        self._passive_states: Set[str] = set()
        self._callbacks: List[Callable[[str, str], None]] = []

    def set_passive_states(self, passive_states: List[str]):
        """设置被动状态列表（从皮肤配置读取）"""
        self._passive_states = set(passive_states)

    def is_passive(self, state: str) -> bool:
        """检查是否为被动状态"""
        return state in self._passive_states

    def set_state(self, new_state: str):
        """设置新状态"""
        if new_state == self.current_state:
            return
        old_state = self.current_state
        self.current_state = new_state
        for cb in self._callbacks:
            cb(old_state, new_state)

    def on_state_change(self, callback: Callable[[str, str], None]):
        """注册状态变化回调"""
        self._callbacks.append(callback)