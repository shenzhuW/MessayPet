# systems/ai/memory.py
import json
import os
import time
from typing import List, Dict, Any


class ConversationMemory:
    # 短期记忆：保留最近3天内的对话
    SHORT_TERM_DAYS = 3

    def __init__(self, storage_dir: str = None, max_messages: int = 50):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.expanduser("~"), ".deskpet", "data", "conversation")
        self.storage_dir = storage_dir
        self.max_messages = max_messages
        os.makedirs(storage_dir, exist_ok=True)

        self.session_id = None
        self.session_file = None
        self.messages: List[Dict] = []
        self.summary = ""
        self.date = ""

    def start_session(self, session_id: str = None):
        self.session_id = session_id or f"{time.strftime('%Y-%m-%d')}_{int(time.time())}"
        self.date = time.strftime("%Y-%m-%d")
        self.session_file = os.path.join(self.storage_dir, f"{self.session_id}.json")

        if os.path.exists(self.session_file):
            self._load()
        else:
            self.messages = []
            self.summary = ""

        # 清理过期文件（超过 SHORT_TERM_DAYS 天的会话文件）
        self._cleanup_old_sessions()

    def _cleanup_old_sessions(self):
        """清理超过短期记忆期限的会话文件"""
        if not os.path.exists(self.storage_dir):
            return

        cutoff_time = time.time() - (self.SHORT_TERM_DAYS * 24 * 60 * 60)
        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.storage_dir, filename)
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)

    def add(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": int(time.time())
        })
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_messages(self) -> List[Dict]:
        return self.messages.copy()

    def get_recent(self, limit: int = 5) -> str:
        """获取最近的对话内容（用于气泡生成）"""
        recent = self.messages[-limit:] if len(self.messages) > limit else self.messages
        if not recent:
            return ""
        lines = []
        for msg in recent:
            role = "宠物" if msg.get("role") == "assistant" else "主人"
            lines.append(f"{role}说：{msg.get('content', '')}")
        return "；".join(lines)

    def set_summary(self, summary: str):
        self.summary = summary

    def save(self):
        data = {
            "session_id": self.session_id,
            "date": self.date,
            "messages": self.messages,
            "summary": self.summary
        }
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        with open(self.session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.session_id = data.get("session_id", self.session_id)
        self.date = data.get("date", self.date)
        self.messages = data.get("messages", [])
        self.summary = data.get("summary", "")

class ChatMemory:
    """聊天窗口专用的短期记忆，保留3天，最多30条"""
    SHORT_TERM_DAYS = 3
    MAX_MESSAGES = 30

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            storage_dir = os.path.join(os.path.expanduser("~"), ".deskpet", "data", "chat_history")
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.session_id = None
        self.session_file = None
        self.messages: List[Dict] = []
        self.date = ""

        self._load_or_start()

    def _load_or_start(self):
        """加载今天的数据或创建新会话"""
        today = time.strftime("%Y-%m-%d")
        self.session_file = os.path.join(self.storage_dir, f"chat_{today}.json")

        if os.path.exists(self.session_file):
            self._load()
        else:
            self.session_id = f"chat_{today}_{int(time.time())}"
            self.date = today
            self.messages = []

        self._cleanup_old_sessions()

    def _cleanup_old_sessions(self):
        """清理超过 SHORT_TERM_DAYS 天的会话文件"""
        if not os.path.exists(self.storage_dir):
            return
        cutoff_time = time.time() - (self.SHORT_TERM_DAYS * 24 * 60 * 60)
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("chat_") and filename.endswith('.json'):
                file_path = os.path.join(self.storage_dir, filename)
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)

    def add(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": int(time.time())
        })
        # 超过 MAX_MESSAGES 条时移除最早的
        while len(self.messages) > self.MAX_MESSAGES:
            self.messages.pop(0)
        self.save()

    def get_all(self) -> List[Dict]:
        return self.messages.copy()

    def get_recent(self, limit: int = 30) -> List[Dict]:
        """获取最近的 limit 条消息"""
        return self.messages[-limit:] if len(self.messages) > limit else self.messages.copy()

    def save(self):
        data = {
            "session_id": self.session_id,
            "date": self.date,
            "messages": self.messages
        }
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        with open(self.session_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.session_id = data.get("session_id", self.session_id)
        self.date = data.get("date", self.date)
        self.messages = data.get("messages", [])


class FactMemory:
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = os.path.join(os.path.expanduser("~"), ".deskpet", "data", "memory", "facts.json")
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        self.facts: List[Dict] = []
        self._load()

    def add(self, key: str, value: Any, source: str = "", confidence: float = 1.0):
        for f in self.facts:
            if f["key"] == key:
                f["value"] = value
                f["source"] = source
                f["confidence"] = confidence
                return
        self.facts.append({
            "key": key,
            "value": value,
            "source": source,
            "confidence": confidence
        })
        self.save()

    def get_all(self) -> List[Dict]:
        return self.facts.copy()

    def update(self, key: str, value: Any):
        for f in self.facts:
            if f["key"] == key:
                f["value"] = value
                self.save()
                return
        self.add(key, value)

    def delete(self, key: str):
        self.facts = [f for f in self.facts if f["key"] != key]
        self.save()

    def save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.facts, f, ensure_ascii=False, indent=2)

    def _load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                self.facts = json.load(f)

class UserProfile:
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = os.path.join(os.path.expanduser("~"), ".deskpet", "data", "memory", "user_profile.json")
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        self.data = {
            "name": "",
            "nickname": "",
            "preferences": [],
            "habits": [],
            "relationship": "朋友",
            "created_at": time.strftime("%Y-%m-%d"),
            "updated_at": time.strftime("%Y-%m-%d")
        }
        self._load()

    def set(self, field: str, value: Any):
        self.data[field] = value
        self.data["updated_at"] = time.strftime("%Y-%m-%d")
        self.save()

    def add_to_list(self, field: str, value: Any):
        if field not in self.data:
            self.data[field] = []
        if isinstance(self.data[field], list) and value not in self.data[field]:
            self.data[field].append(value)
            self.data["updated_at"] = time.strftime("%Y-%m-%d")
            self.save()

    def get(self, field: str, default=None):
        return self.data.get(field, default)

    def get_all(self) -> Dict:
        return self.data.copy()

    def save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.data.update(loaded)

class PetProfile:
    DEFAULT_PROFILE = {
        "name": "",
        "gender": "未知",  # 可编辑：公/母/未知
        "species": "橘猫",
        "personality": "活泼好奇、有点话痨、爱撒娇",
        "appearance": "橘色毛发，圆圆的眼睛，脖子上有个小铃铛",
        "background": "住在主人电脑旁边的小精灵，喜欢观察主人工作",
        "speech_style": "可爱俏皮，句尾常用~和^ω^，偶尔用颜文字",
        "abilities": ["卖萌", "安慰人", "讲冷笑话"],
        "likes": ["晒太阳", "零食", "被摸摸"],
        "dislikes": ["打雷", "一个人"]
    }

    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = os.path.join(os.path.expanduser("~"), ".deskpet", "data", "memory", "pet_profile.json")
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        self.data = self.DEFAULT_PROFILE.copy()
        self._load()

    def set(self, field: str, value: Any):
        self.data[field] = value
        self.save()

    def add_to_list(self, field: str, value: Any):
        if field not in self.data:
            self.data[field] = []
        if isinstance(self.data[field], list) and value not in self.data[field]:
            self.data[field].append(value)
            self.save()

    def get(self, field: str, default=None):
        return self.data.get(field, default)

    def get_all(self) -> Dict:
        return self.data.copy()

    def save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.data.update(loaded)