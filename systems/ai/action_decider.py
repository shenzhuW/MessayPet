# systems/ai/action_decider.py
"""LLM 驱动的动作决策器"""
import json
import time
import threading
from dataclasses import dataclass
from typing import List, Optional, Callable, TYPE_CHECKING

from prompts.action import (
    build_role_info,
    build_action_prompt,
    get_time_description,
    ACTION_JSON_FORMAT,
)

if TYPE_CHECKING:
    from systems.ai.llm_client import LLMClient
    from core.animation.skin_manager import SkinManager


@dataclass
class DecisionResult:
    """动作决策结果"""
    action: str
    duration: int
    reason: str = ""
    bubble_text: str = ""  # 执行动作时说的气泡文本


class ActionDecider:
    """基于 LLM 的动作决策器"""

    def __init__(
        self,
        llm_client: 'LLMClient',
        skin_manager: 'SkinManager',
        stat_manager,
        action_history,
        memory_manager=None
    ):
        self.llm_client = llm_client
        self.skin_manager = skin_manager
        self.stat_manager = stat_manager
        self.action_history = action_history
        self.memory_manager = memory_manager
        self._is_deciding = False
        self._callback: Optional[Callable] = None  # 异步结果回调

    @property
    def MOVING_ACTIONS(self) -> set:
        """获取移动类动作（从皮肤配置或默认）"""
        return set(self.skin_manager.get_moving_actions())

    @property
    def STATE_ACTIONS(self) -> set:
        """获取状态类动作（从皮肤配置或默认）"""
        return set(self.skin_manager.get_state_actions())

    def get_available_actions(self) -> List[str]:
        """获取当前皮肤的可交互动作（可由 LLM 决策，不含被动动作）"""
        return self.skin_manager.get_interactive_actions()

    def decide_next_action(self, callback: Optional[Callable[['DecisionResult'], None]] = None):
        """请求 LLM 决定下一个动作（异步版本，避免阻塞主线程）

        Args:
            callback: 可选的回调函数，接收 DecisionResult 或 None
        """
        if self._is_deciding:
            if callback:
                callback(None)
            return
        self._is_deciding = True
        self._callback = callback

        def run_in_thread():
            try:
                prompt = self._build_decision_prompt()
                print(f"\n========== [ActionDecider] Prompt ==========\n{prompt}\n==========================================")
                response = self.llm_client.chat_complete(prompt)
                print(f"\n========== [ActionDecider] Response ==========\n{response}\n==========================================")
                result = None
                if response and response != "[Timeout]":
                    result = self._parse_decision(response)
                # 直接调用回调（通过 Qt Signal 在主线程执行）
                if self._callback:
                    self._callback(result)
            except Exception as e:
                print(f"[ActionDecider] Error: {e}")
                if self._callback:
                    self._callback(None)
            finally:
                self._is_deciding = False

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

    def _build_decision_prompt(self) -> str:
        """构建决策 prompt"""
        # 构建角色信息
        role_info = ""
        if self.memory_manager:
            profile = self.memory_manager.get_pet_profile()
            role_info = build_role_info(
                name=profile.get("name", ""),
                species=profile.get("species", ""),
                personality=profile.get("personality", ""),
                speech_style=profile.get("speech_style", "")
            )

        # 获取状态
        stats = self.stat_manager.get_stats() if self.stat_manager else None

        # 获取可用动作
        available = self.get_available_actions()
        moving = list(self.MOVING_ACTIONS)
        state = list(self.STATE_ACTIONS)

        # 获取动作描述
        descriptions = self.skin_manager.get_action_descriptions()

        # 获取动作历史
        action_history = self.action_history.to_prompt_string() if self.action_history else ""

        # 获取已知事实
        known_facts = []
        if self.memory_manager and hasattr(self.memory_manager, 'facts'):
            all_facts = self.memory_manager.facts.get_all()
            if all_facts:
                known_facts = [f for f in all_facts if f.get("confidence", 0) >= 0.7]

        # 获取气泡历史
        bubble_history = self.action_history.to_bubble_prompt_string() if self.action_history else ""

        return build_action_prompt(
            role_info=role_info,
            stats=stats,
            available_actions=available,
            moving_actions=moving,
            state_actions=state,
            action_descriptions=descriptions,
            action_history=action_history,
            bubble_history=bubble_history,
            known_facts=known_facts
        )

    def _parse_decision(self, response: str) -> Optional[DecisionResult]:
        """解析 LLM 响应"""
        if not response:
            return None

        # 移除 <think> 和</think>
        import re
        text = re.sub(r'<think>\s*[\s\S]*?\s*</think>', '', response, flags=re.IGNORECASE).strip()

        # 提取 JSON
        json_str = self._extract_json(text)
        if not json_str:
            return None

        try:
            data = json.loads(json_str)
            # print(f"[ActionDecider] Decision: {json_str}")
            action = data.get("action", "")
            duration = int(data.get("duration", 5))
            reason = data.get("reason", "")
            bubble_text = data.get("bubble_text", "")

            # 验证动作是否可用
            available = self.get_available_actions()
            if action not in available:
                print(f"[ActionDecider] 动作 '{action}' 不可用，使用随机选择")
                import random
                action = random.choice(available) if available else "idle"

            # 限制 duration 范围
            if action in self.MOVING_ACTIONS:
                duration = max(3, min(10, duration))
            else:
                duration = max(5, min(20, duration))

            return DecisionResult(action=action, duration=duration, reason=reason, bubble_text=bubble_text)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ActionDecider] 解析失败: {e}")
            print(f"  Response: {response[:200]}")
            return None

    def _extract_json(self, text: str) -> str:
        """提取 JSON 字符串"""
        import re

        # 方式1: ```json ... ```
        match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 方式2: 直接找 {...}
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return match.group(0)

        return ""