# core/stat_manager.py
import json
import os
import time
from dataclasses import dataclass
from typing import Dict

# XP needed per level: level * 100
XP_PER_LEVEL = 100


@dataclass
class StatConfig:
    max_values: Dict[str, float] = None
    decay_rates: Dict[str, float] = None
    health_hungry_threshold: float = 30.0

    def __post_init__(self):
        if self.max_values is None:
            self.max_values = {"hunger": 100, "mood": 100, "health": 100, "thirst": 100}
        if self.decay_rates is None:
            self.decay_rates = {"hunger": 0.0028, "mood": 0.0056, "health": 0.0, "thirst": 0.0033}


class StatManager:
    """Manages pet stats, level progression, and intimacy."""

    MAX_STAT = 100
    MIN_STAT = 0

    def __init__(self, config: StatConfig = None, config_dir: str = None):
        self.config = config or StatConfig()
        self.config_dir = config_dir or os.path.join(os.path.expanduser("~"), ".deskpet", "data")
        os.makedirs(self.config_dir, exist_ok=True)
        self.stats_file = os.path.join(self.config_dir, "stats.json")

        self.hunger = 100.0
        self.mood = 100.0
        self.health = 100.0
        self.thirst = 100.0  # 饥渴值
        self.intimacy = 0.0
        self.xp = 0
        self.level = 1
        self._energy = 100.0
        self._age = 0
        self._birth_time = 0  # 出生时间戳

        self._decay_rates = self.config.decay_rates
        self._load()
        # 如果没有出生时间，设置当前时间为出生时间
        if self._birth_time == 0:
            self._birth_time = time.time()
            self.save()

    def _load(self):
        if os.path.exists(self.stats_file):
            with open(self.stats_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.hunger = loaded.get("hunger", 100)
                self.mood = loaded.get("mood", 100)
                self.health = loaded.get("health", 100)
                self.thirst = loaded.get("thirst", 100)
                self.intimacy = loaded.get("intimacy", 0)
                self.xp = loaded.get("xp", 0)
                self.level = loaded.get("level", 1)
                self._energy = loaded.get("energy", 100)
                self._age = loaded.get("age", 0)
                self._birth_time = loaded.get("birth_time", 0)

    def save(self):
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

    def tick(self, dt: float):
        """Update stats over time (called every second)."""
        self.hunger = max(0, self.hunger - self._decay_rates.get("hunger", 0) * dt)
        self.thirst = max(0, self.thirst - self._decay_rates.get("thirst", 0) * dt)
        self.mood = max(0, self.mood - self._decay_rates.get("mood", 0) * dt)

        # Health degrades when hungry or mood is low (<30)
        if self.hunger < 30 or self.mood < 30:
            self.health = max(0, self.health - 0.0028 * dt)  # 半小时衰减5点

        # Energy decay: 5 points per 30 minutes = 0.00278 per second
        self._energy = max(0, self._energy - 0.00278 * dt)

    def get_age_days(self) -> float:
        """获取宠物年龄（天数），基于真实时间计算"""
        print(f"[StatManager] get_age_days: _birth_time={self._birth_time}")
        if self._birth_time > 0:
            return (time.time() - self._birth_time) / 86400.0  # 秒转天数
        return 0.0

    def get_birth_date(self) -> str:
        """获取出生日期字符串"""
        print(f"[StatManager] get_birth_date: _birth_time={self._birth_time}")
        if self._birth_time > 0:
            from datetime import datetime as dt
            return dt.fromtimestamp(self._birth_time).strftime("%Y-%m-%d")
        return ""

    def feed(self, amount: float = 20):
        self.hunger = min(100, self.hunger + amount)
        self.health = min(100, self.health + 5)  # 喂食也恢复健康

    def drink(self, amount: float = 20):
        """喝水恢复饥渴值"""
        self.thirst = min(100, self.thirst + amount)

    def play(self):
        self.mood = min(100, self.mood + 15)
        self.add_xp(10)
        self._energy = max(0, self._energy - 5)

    def rest(self):
        self._energy = min(100, self._energy + 30)
        self.health = min(100, self.health + 10)  # 休息恢复健康

    def on_interaction(self, action_type: str = "general"):
        intimacy_gain = {"pet": 10, "feed": 15, "play": 15, "talk": 5, "general": 5}
        gain = intimacy_gain.get(action_type, 5)
        self.intimacy = min(1000, self.intimacy + gain)
        self.add_xp(5)

    def add_xp(self, amount: int):
        self.xp += amount
        xp_needed = self.level * XP_PER_LEVEL
        while self.xp >= xp_needed:
            self.xp -= xp_needed
            self.level += 1
            xp_needed = self.level * XP_PER_LEVEL

    def has_unlocked(self, unlock_level: int) -> bool:
        return self.level >= unlock_level

    def to_dict(self) -> dict:
        return {
            "hunger": self.hunger,
            "mood": self.mood,
            "health": self.health,
            "thirst": self.thirst,
            "intimacy": self.intimacy,
            "xp": self.xp,
            "level": self.level,
            "energy": self._energy,
            "age": self._age,
            "birth_time": self._birth_time,
        }

    @classmethod
    def from_dict(cls, data: dict, config: StatConfig = None, config_dir: str = None) -> "StatManager":
        stats = cls(config, config_dir)
        stats.hunger = data.get("hunger", 100)
        # 如果 data 中的 birth_time 为 0，保留已有的出生时间
        birth_time = data.get("birth_time", 0)
        if birth_time > 0:
            stats._birth_time = birth_time
        stats.mood = data.get("mood", 100)
        stats.health = data.get("health", 100)
        stats.intimacy = data.get("intimacy", 0)
        stats.xp = data.get("xp", 0)
        stats.level = data.get("level", 1)
        stats._energy = data.get("energy", 100)
        stats._age = data.get("age", 0)
        return stats

    def get_stats(self) -> Dict[str, int]:
        return {
            "hunger": int(self.hunger),
            "mood": int(self.mood),
            "health": int(self.health),
            "thirst": int(self.thirst),
            "intimacy": int(self.intimacy),
            "level": self.level,
            "xp": self.xp,
            "energy": int(self._energy),
            "age": int(self._age),
        }