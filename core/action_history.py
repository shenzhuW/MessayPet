# core/action_history.py
"""动作历史记录器"""
import time
from dataclasses import dataclass
from typing import List


@dataclass
class ActionRecord:
    """单条动作记录"""
    action: str
    duration: int
    timestamp: float


@dataclass
class BubbleRecord:
    """气泡历史记录"""
    text: str
    timestamp: float
    source: str = ""  # 来源：random, window_change, hook_complete, hook_waiting, click, interaction 等


class ActionHistory:
    """动作历史管理器"""

    def __init__(self, max_size: int = 10, bubble_max_size: int = 10):
        self._records: List[ActionRecord] = []
        self._max_size = max_size
        self._bubble_records: List[BubbleRecord] = []
        self._bubble_max_size = 20  # 限制为最近20条
        self._current_action: str = ""  # 当前正在执行的动作
        self._last_choice: str = ""  # 用户上次选择的选项

    def set_current_action(self, action: str):
        """设置当前正在执行的动作"""
        self._current_action = action

    def clear_current_action(self):
        """清除当前动作（动作完成时调用）"""
        self._current_action = ""

    def get_current_action(self) -> str:
        """获取当前正在执行的动作"""
        return self._current_action

    def set_last_choice(self, choice: str):
        """设置用户选择的选项"""
        self._last_choice = choice

    def get_last_choice(self) -> str:
        """获取用户上次选择的选项"""
        return self._last_choice

    def add(self, action: str, duration: int):
        """添加动作记录"""
        self._records.append(ActionRecord(
            action=action,
            duration=duration,
            timestamp=time.time()
        ))
        if len(self._records) > self._max_size:
            self._records.pop(0)

    def add_bubble(self, text: str, source: str = ""):
        """添加气泡历史记录

        Args:
            text: 气泡文本
            source: 来源标识，如 "random"（随机气泡）、"window_change"（窗口切换）、
                   "hook_complete"（任务完成）、"hook_waiting"（任务等待）、"click"（点击）等
        """
        if not text:
            return
        self._bubble_records.append(BubbleRecord(
            text=text,
            timestamp=time.time(),
            source=source or "unknown"
        ))
        if len(self._bubble_records) > self._bubble_max_size:
            self._bubble_records.pop(0)

    def get_recent(self, limit: int = None) -> List[ActionRecord]:
        """获取最近的动作记录"""
        if limit is None:
            return self._records.copy()
        return self._records[-limit:]

    def get_last_action(self) -> str:
        """获取上一个动作"""
        if self._records:
            return self._records[-1].action
        return None

    def get_last_n_actions(self, n: int) -> List[str]:
        """获取最近 N 个动作名称"""
        return [r.action for r in self._records[-n:]]

    def get_recent_bubbles(self, limit: int = None) -> List[BubbleRecord]:
        """获取最近的气泡记录"""
        if limit is None:
            return self._bubble_records.copy()
        return self._bubble_records[-limit:]

    def get_last_bubble_text(self) -> str:
        """获取上一个气泡文本"""
        if self._bubble_records:
            return self._bubble_records[-1].text
        return None

    def clear(self):
        """清空历史"""
        self._records.clear()
        self._bubble_records.clear()

    def to_prompt_string(self, limit: int = 10) -> str:
        """转换为用于 prompt 的字符串（显示最新 limit 条）"""
        recent = self.get_recent(limit)
        if not recent:
            return "（无历史）"

        lines = []
        # 只显示最新的 limit 条
        display_records = recent[-limit:] if len(recent) > limit else recent
        for record in display_records:
            lines.append(f"- {record.action}（{record.duration}秒）")
        return "\n".join(lines) if lines else "（无历史）"

    def to_bubble_prompt_string(self, limit: int = 10) -> str:
        """转换为气泡历史用于 prompt 的字符串"""
        recent = self.get_recent_bubbles(limit)
        if not recent:
            return "（无气泡历史）"

        source_names = {
            "random": "随机",
            "window_change": "窗口切换",
            "hook_complete": "任务完成",
            "hook_waiting": "任务等待",
            "click": "点击互动",
            "interaction": "互动",
            "unknown": "未知"
        }

        lines = []
        for record in recent:
            source_name = source_names.get(record.source, record.source)
            lines.append(f"- [{source_name}] \"{record.text}\"")
        return "\n".join(lines) if lines else "（无气泡历史）"