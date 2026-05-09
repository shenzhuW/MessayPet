import random
from typing import Dict


class BubblePersonality:
    """宠物性格系统 - 影响回复风格"""

    PERSONALITY_TYPES = {
        "cute": {
            "name": "可爱萌系",
            "style_hint": "说话带语气词，喜欢用叠词，如'主人'、'喵~'、'好开心呀~'",
            "expressions": ["喵~", "嘿嘿~", "呀~", "呜~"]
        },
        "cool": {
            "name": "高冷系",
            "style_hint": "话少高冷，偶尔傲娇，回复简短有力",
            "expressions": ["哼", "...", "知道了", "随你"]
        },
        "playful": {
            "name": "调皮系",
            "style_hint": "活泼调皮，喜欢开玩笑，会主动撩人",
            "expressions": ["嘿嘿嘿~", "来抓我呀~", "笨蛋~"]
        },
        "gentle": {
            "name": "温柔系",
            "style_hint": "温柔体贴，关心主人，善于倾听",
            "expressions": ["乖~", "别累着哦~", "我陪着你~"]
        },
        "energetic": {
            "name": "元气系",
            "style_hint": "元气满满，充满活力，总是很兴奋",
            "expressions": ["冲鸭！", "太棒啦！", "走起！"]
        }
    }

    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self._current_type = "cute"  # 默认可爱萌系

    def set_personality(self, personality_type: str):
        """设置性格类型"""
        if personality_type in self.PERSONALITY_TYPES:
            self._current_type = personality_type

    def get_current_personality(self) -> Dict:
        """获取当前性格配置"""
        return self.PERSONALITY_TYPES.get(self._current_type, self.PERSONALITY_TYPES["cute"])

    def get_personality_name(self) -> str:
        """获取当前性格名称"""
        p = self.get_current_personality()
        return p.get("name", "可爱萌系")

    @staticmethod
    def get_all_types() -> Dict[str, Dict]:
        """获取所有性格类型"""
        return BubblePersonality.PERSONALITY_TYPES.copy()

    def get_expression(self) -> str:
        """获取当前性格的表情词"""
        p = self.get_current_personality()
        return random.choice(p["expressions"])