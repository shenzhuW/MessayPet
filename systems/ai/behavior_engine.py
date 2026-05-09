# systems/ai/behavior_engine.py
import time
import random
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class BehaviorTrigger(Enum):
    TIME = "time"
    STAT_LOW = "stat_low"
    RANDOM = "random"
    WINDOW_CHANGE = "window"


@dataclass
class Behavior:
    id: str
    text: str
    min_level: int = 1
    trigger: BehaviorTrigger = BehaviorTrigger.RANDOM
    cooldown: int = 300
    stat_threshold: Optional[str] = None


ALL_BEHAVIORS = [
    # Lv.1 — Basic
    Behavior("greet", "Hello! Want to chat?", min_level=1),
    Behavior("cute", "*does a little dance*", min_level=1),
    Behavior("bounce", "*bounces happily*", min_level=1),

    # Lv.5 — Chatty
    Behavior("complain", "I'm getting a bit bored...", min_level=5, trigger=BehaviorTrigger.RANDOM),
    Behavior("morning", "Good morning! How's your day going?", min_level=5, trigger=BehaviorTrigger.TIME),
    Behavior("curious", "What are you working on?", min_level=5),

    # Lv.10 — Engaged
    Behavior("joke", "Why did the developer go broke? Because he used up all his cache!", min_level=10, cooldown=600),
    Behavior("reminder", "Don't forget to take a break every hour!", min_level=10, cooldown=900),
    Behavior("observation", "You've been coding for a while. Want a snack?", min_level=10),

    # Lv.15 — Caring
    Behavior("care_hungry", "I'm hungry... do you have any treats?", min_level=15, trigger=BehaviorTrigger.STAT_LOW, stat_threshold="hunger<30"),
    Behavior("care_mood", "You seem stressed. Want me to tell a joke?", min_level=15, trigger=BehaviorTrigger.STAT_LOW, stat_threshold="mood<30"),
    Behavior("memory_mention", "I remember you said you like cats!", min_level=15, cooldown=600),

    # Lv.20 — Complex
    Behavior("deep_chat", "What do you think about the future of AI?", min_level=20),
    Behavior("empathy", "I can tell something's on your mind. I'm here if you want to talk.", min_level=20),
]


class BehaviorEngine:
    def __init__(self, level: int = 1, event_bus=None):
        self.level = level
        self.event_bus = event_bus
        self._last_trigger_time: Dict[str, float] = {}
        self._cooldown_default = 300

    def get_available_behaviors(self) -> List[Behavior]:
        return [b for b in ALL_BEHAVIORS if b.min_level <= self.level]

    def can_trigger(self, behavior_id: str) -> bool:
        last = self._last_trigger_time.get(behavior_id, 0)
        behavior = next((b for b in ALL_BEHAVIORS if b.id == behavior_id), None)
        if not behavior:
            return False
        return (time.time() - last) >= behavior.cooldown

    def record_trigger(self, behavior_id: str):
        self._last_trigger_time[behavior_id] = time.time()

    def select_behavior(self, stats: Dict[str, float]) -> Optional[Behavior]:
        available = self.get_available_behaviors()
        if not available:
            return None

        # Priority: stat-based triggers first
        for b in available:
            if b.trigger == BehaviorTrigger.STAT_LOW and self._check_stat_condition(b, stats):
                if self.can_trigger(b.id):
                    return b

        # Then random
        candidates = [b for b in available if b.trigger == BehaviorTrigger.RANDOM and self.can_trigger(b.id)]
        if candidates:
            return random.choice(candidates)

        return None

    def _check_stat_condition(self, behavior: Behavior, stats: Dict[str, float]) -> bool:
        if not behavior.stat_threshold:
            return False
        parts = behavior.stat_threshold.split("<")
        if len(parts) == 2:
            stat_name = parts[0].strip()
            threshold = float(parts[1].strip())
            return stats.get(stat_name, 100) < threshold
        return False