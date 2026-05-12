import time
import threading
from datetime import datetime
from typing import Callable, Optional, Dict
from PySide6.QtCore import Signal, QObject
from core.emotion import EmotionState
from core.event_bus import EventType
from prompts.emotion import (
    build_interaction_prompt,
    build_window_change_prompt,
    build_random_prompt,
    build_analysis_user_message,
    get_time_description,
)


class EmotionAnalyzer(QObject):
    """LLM 驱动的情绪分析 + 气泡生成"""

    # Signal to show bubble from main thread (text, choices, source)
    bubble_ready = Signal(str, list, str)

    def __init__(self, llm_client, memory_manager, stat_manager, window_monitor, event_bus=None, action_history=None):
        super().__init__()
        self.llm_client = llm_client
        self.memory_manager = memory_manager
        self.stat_manager = stat_manager
        self.window_monitor = window_monitor
        self.event_bus = event_bus
        self.action_history = action_history
        self._last_analysis_time = 0
        self._last_emotion: Optional[Dict] = None
        self._is_analyzing = False
        self._current_interaction: Optional[str] = None  # 当前互动类型

    def _get_pet_profile(self) -> Dict:
        """获取宠物角色卡配置"""
        if self.memory_manager and hasattr(self.memory_manager, 'pet_profile'):
            return self.memory_manager.pet_profile.get_all()
        return {}

    def analyze_and_generate(self, trigger_type: str = "interaction", interaction: str = None):
        """LLM 分析情绪并生成气泡（通过 bubble_ready signal 传递结果）

        Args:
            trigger_type: 触发类型 - "interaction"（互动）、"random"（随机）、"click"（点击）
            interaction: 互动方式 - "喂食"、"玩耍"、"休息"
        """
        if self._is_analyzing:
            return

        self._current_interaction = interaction
        self._do_analyze(trigger_type)

    def _do_analyze(self, trigger_type: str = "interaction"):
        self._is_analyzing = True

        def run_in_thread():
            try:
                prompt = self._build_analysis_prompt(trigger_type)
                user_message = build_analysis_user_message(prompt)

                print(f"\n========== [EmotionAnalyzer] Prompt ==========\n{user_message}\n==========================================")

                response = self.llm_client.chat_complete(user_message)

                print(f"\n========== [EmotionAnalyzer] Response ==========\n{response}\n==========================================")

                if response and response != "[Timeout]":
                    result = self._parse_response(response)
                    if result:
                        emotion, intensity, reason, bubble_text, choices = result
                        self._last_emotion = {
                            "emotion": emotion,
                            "intensity": intensity,
                            "reason": reason
                        }
                        self._last_analysis_time = time.time()

                        # 发布情绪变化事件
                        if self.event_bus:
                            self.event_bus.publish(EventType.EMOTION_CHANGED, {
                                "emotion": emotion,
                                "intensity": intensity,
                                "reason": reason
                            })

                        # 发送气泡信号（带上 choices 和来源）
                        self.bubble_ready.emit(bubble_text, choices, trigger_type)

            except Exception as e:
                import traceback
                traceback.print_exc()
            finally:
                self._is_analyzing = False

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

    def _build_analysis_prompt(self, trigger_type: str = "interaction") -> str:
        """构建完整的 LLM 分析上下文"""
        profile = self._get_pet_profile()

        # 获取记忆数据
        facts_list = []
        user_likes = []
        recent_conversation = ""
        if self.memory_manager:
            if hasattr(self.memory_manager, 'facts'):
                facts_list = self.memory_manager.facts.get_all()
            if hasattr(self.memory_manager, 'user_profile'):
                user_data = self.memory_manager.user_profile.get_all()
                user_likes = user_data.get("preferences", [])
            if hasattr(self.memory_manager, 'conversation'):
                recent_conversation = self.memory_manager.conversation.get_recent(limit=20)

        # 获取动作历史
        action_history = ""
        if self.action_history:
            action_history = self.action_history.to_prompt_string()

        # 获取当前正在执行的动作
        current_action = ""
        if self.action_history:
            current_action = self.action_history.get_current_action() or ""

        # 获取用户上次选择的选项
        last_choice = ""
        if self.action_history:
            last_choice = self.action_history.get_last_choice() or ""

        # 获取当前窗口
        current_window = self.window_monitor.get_current_title() if self.window_monitor else ""

        # 获取状态
        stats = self.stat_manager.get_stats() if self.stat_manager else None

        # 根据触发类型选择不同的构建方式
        if trigger_type == "interaction":
            return build_interaction_prompt(
                profile=profile,
                interaction=self._current_interaction or "互动",
                stats=stats,
                current_window=current_window,
                known_facts=facts_list,
                user_likes=user_likes,
                recent_conversation=recent_conversation,
                action_history=action_history,
                current_action=current_action,
                last_choice=last_choice
            )
        elif trigger_type == "window_change":
            return build_window_change_prompt(
                profile=profile,
                stats=stats,
                current_window=current_window,
                known_facts=facts_list,
                user_likes=user_likes,
                recent_conversation=recent_conversation,
                action_history=action_history,
                current_action=current_action,
                last_choice=last_choice
            )
        else:
            return build_random_prompt(
                profile=profile,
                stats=stats,
                current_window=current_window,
                known_facts=facts_list,
                user_likes=user_likes,
                recent_conversation=recent_conversation,
                action_history=action_history,
                current_action=current_action,
                last_choice=last_choice
            )

    def _parse_response(self, text: str) -> Optional[tuple]:
        """解析 LLM 返回，提取情绪 + 气泡文本"""
        import re
        import json

        if not text:
            return None

        original_text = text

        # 第一步：去除<think>和</think>包裹的内容
        def remove_think_tags(text: str) -> str:
            """递归移除最内层的 <think>...</think> 对"""
            # 直接删除整个 <think>...</think> 块
            pattern = re.compile(r'<think>\s*[\s\S]*?\s*</think>', re.IGNORECASE)
            while True:
                new_text = pattern.sub('', text)
                if new_text == text:
                    break
                text = new_text
            return text

        text = remove_think_tags(text)
        text = text.strip()

        # 第二步：提取 JSON（多种方式）
        json_str = ""

        # 方式1: ```json ... ```
        json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text, re.IGNORECASE)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # 方式2: 直接找第一个 {...} 块
            json_str = self._extract_first_json(text)
            if not json_str:
                # 方式3: 尝试从后往前找最后一个完整 {...}
                json_str = self._extract_last_json(text)

        # 第三步：解析 JSON
        if json_str:
            try:
                data = json.loads(json_str)
                emotion = data.get("emotion", "neutral")
                intensity = float(data.get("intensity", 0.5))
                reason = data.get("reason", "")
                bubble_text = data.get("bubble_text", "")
                choices = data.get("choices", [])

                # 验证情绪有效性
                if emotion not in EmotionState.VALID_EMOTIONS:
                    emotion_map = {
                        "开心": "happy", "高兴": "happy", "快乐": "happy",
                        "委屈": "sad", "难过": "sad", "伤心": "sad",
                        "困倦": "sleepy", "困": "sleepy", "累": "sleepy",
                        "饥饿": "hungry", "饿": "hungry",
                        "好奇": "curious", "好奇的": "curious",
                        "平静": "neutral", "普通": "neutral",
                        "兴奋": "excited", "激动": "excited",
                    }
                    for cn, en in emotion_map.items():
                        if cn in emotion:
                            emotion = en
                            break
                    if emotion not in EmotionState.VALID_EMOTIONS:
                        emotion = "neutral"

                return (emotion, intensity, reason, bubble_text.strip(), choices)

            except (json.JSONDecodeError, ValueError) as e:
                print(f"[EmotionAnalyzer] JSON parse error: {e}, trying fallback...")
                print(f"  JSON string: {json_str[:200]}")

        # 第四步：Fallback - 直接从纯文本提取
        # print(f"[EmotionAnalyzer] Fallback: extracting from raw text")
        # print(f"  Raw text: {text}")

        # 尝试直接提取 bubble_text
        bubble_match = re.search(r'bubble_text["\s:]+[""\']([^""\']+)[""\']', text, re.IGNORECASE)
        if bubble_match:
            bubble_text = bubble_match.group(1)
        else:
            # 直接用最后一段非think的文字
            bubble_text = text.strip()[:20]

        if bubble_text:
            # 过滤无效内容（看起来像代码、思考过程、或乱码）
            invalid_patterns = ['emotion_analyzer', 'EmotionAnalyzer', 'analysis', '```', 'def ', 'class ',
                              'import ', '{', '}', 'null', 'undefined', 'True', 'False',
                              'is_thrown', 'is_analyzing', 'bubble_ready', 'signal']
            for pattern in invalid_patterns:
                if pattern in bubble_text and len(bubble_text) < 30:
                    print(f"[EmotionAnalyzer] Filtered invalid content: {bubble_text}")
                    return None
            return ("neutral", 0.5, "fallback", bubble_text)

        return None

    def _extract_first_json(self, text: str) -> str:
        """提取第一个完整的 JSON 对象"""
        brace_start = text.find('{')
        if brace_start < 0:
            return ""
        # 找匹配的闭合括号
        depth = 0
        for i, c in enumerate(text[brace_start:], brace_start):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[brace_start:i+1]
        return ""

    def _extract_last_json(self, text: str) -> str:
        """从后往前提取最后一个完整的 JSON 对象"""
        brace_end = text.rfind('}')
        if brace_end < 0:
            return ""
        # 从 brace_end 往前找匹配的起始 {
        depth = 0
        for i in range(brace_end, -1, -1):
            c = text[i]
            if c == '}':
                depth += 1
            elif c == '{':
                depth -= 1
                if depth == 0:
                    return text[i:brace_end+1]
        return ""

    def get_last_emotion(self) -> Optional[Dict]:
        return self._last_emotion

    def get_current_emotion_state(self) -> EmotionState:
        """获取当前情绪状态对象"""
        state = EmotionState()
        if self._last_emotion:
            state.update_from_analysis(
                self._last_emotion.get("emotion", "neutral"),
                self._last_emotion.get("intensity", 0.5),
                self._last_emotion.get("reason", "")
            )
        return state