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


class ActionHistory:
    """动作历史管理器"""

    def __init__(self, max_size: int = 10):
        self._records: List[ActionRecord] = []
        self._max_size = max_size

    def add(self, action: str, duration: int):
        """添加动作记录"""
        self._records.append(ActionRecord(
            action=action,
            duration=duration,
            timestamp=time.time()
        ))
        if len(self._records) > self._max_size:
            self._records.pop(0)

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

    def clear(self):
        """清空历史"""
        self._records.clear()

    def to_prompt_string(self, limit: int = 10) -> str:
        """转换为用于 prompt 的字符串"""
        recent = self.get_recent(limit)
        if not recent:
            return "（无历史）"

        lines = []
        for i, record in enumerate(recent):
            time_ago = int(time.time() - record.timestamp)
            lines.append(f"{i+1}. {record.action}（{record.duration}秒）")
        return "\n".join(lines)