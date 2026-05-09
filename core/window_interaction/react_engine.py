import random
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class Reaction:
    """反应数据"""
    type: str
    duration: int  # 毫秒
    text: Optional[str]


REACTIONS = [
    Reaction(type="yawn", duration=2000, text="好困..."),
    Reaction(type="stare", duration=1500, text="盯..."),
    Reaction(type="curious", duration=2500, text="这是什么？"),
    Reaction(type="stretch", duration=1000, text="伸个懒腰~"),
    Reaction(type="ignore", duration=0, text=None),
]


class ReactEngine:
    """窗口切换反应引擎"""

    def __init__(self):
        self._current_reaction: Optional[Reaction] = None
        self._on_reaction_callback: Optional[Callable] = None

    def set_reaction_callback(self, callback: Callable[[Reaction], None]):
        """设置反应回调"""
        self._on_reaction_callback = callback

    def on_window_changed(self, old_hwnd: int, new_hwnd: int):
        """窗口切换时触发反应"""
        reaction = self.get_random_reaction()
        if reaction and reaction.type != "ignore":
            self._current_reaction = reaction
            if self._on_reaction_callback:
                self._on_reaction_callback(reaction)

    def get_random_reaction(self) -> Reaction:
        """获取随机反应"""
        return random.choice(REACTIONS)

    def clear_reaction(self):
        """清除当前反应"""
        self._current_reaction = None

    def get_current_reaction(self) -> Optional[Reaction]:
        """获取当前反应"""
        return self._current_reaction