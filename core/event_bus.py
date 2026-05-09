from typing import Callable, Dict, List, Any
import uuid

class EventType:
    PET_CLICKED = "pet.clicked"
    PET_DRAGGED = "pet.dragged"
    PET_THROWN = "pet.thrown"
    PET_LANDED = "pet.landed"
    AI_RESPONSE = "ai.response"
    AI_THOUGHT = "ai.thought"
    STAT_CHANGED = "stat.changed"
    WINDOW_CHANGED = "window.changed"
    SKIN_CHANGED = "skin.changed"
    EMOTION_CHANGED = "emotion.changed"

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[tuple]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> str:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        token = str(uuid.uuid4())
        self._handlers[event_type].append((token, handler))
        return token

    def unsubscribe(self, event_type: str, token: str):
        if event_type in self._handlers:
            self._handlers[event_type] = [
                (t, h) for t, h in self._handlers[event_type] if t != token
            ]
            if not self._handlers[event_type]:
                del self._handlers[event_type]

    def publish(self, event_type: str, data: Any = None):
        if event_type in self._handlers:
            for token, handler in self._handlers[event_type]:
                handler(data)