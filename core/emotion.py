class EmotionState:
    """情绪状态管理 - 存储 LLM 返回的情绪结果，驱动动画"""

    VALID_EMOTIONS = ["happy", "sad", "sleepy", "hungry", "curious", "neutral", "excited"]

    def __init__(self):
        self.current: str = "neutral"
        self.intensity: float = 0.5
        self.reason: str = ""
        self.last_updated: float = 0

    def update_from_analysis(self, emotion: str, intensity: float, reason: str):
        """从 LLM 分析结果更新情绪"""
        if emotion in self.VALID_EMOTIONS:
            self.current = emotion
        self.intensity = max(0.0, min(1.0, intensity))
        self.reason = reason
        self.last_updated = _get_time()

    def get_animation_state(self) -> str:
        """情绪 → 动画状态映射"""
        mapping = {
            "happy": "happy",
            "sad": "sad",
            "excited": "happy",
            "sleepy": "idle",
            "hungry": "sad",
            "curious": "idle",
            "neutral": "idle",
        }
        return mapping.get(self.current, "idle")

    def get_animation_speed(self) -> float:
        """情绪影响动画速度"""
        if self.current == "excited":
            return 1.5
        elif self.current == "sleepy":
            return 0.5
        return 1.0


def _get_time():
    import time
    return time.time()