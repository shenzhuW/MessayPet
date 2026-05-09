from systems.ai.memory import ConversationMemory, FactMemory, UserProfile, PetProfile
from systems.ai.context_builder import ContextBuilder
from systems.ai.memory_parser import MemoryParser
from typing import List, Dict

class MemoryManager:
    def __init__(self):
        self.conversation = ConversationMemory()
        self.facts = FactMemory()
        self.user_profile = UserProfile()
        self.pet_profile = PetProfile()
        self.context_builder = ContextBuilder()
        self.parser = MemoryParser()

        self.conversation.start_session()

    def build_context(self) -> List[Dict]:
        return self.context_builder.build(
            self.pet_profile,
            self.user_profile,
            self.facts,
            self.conversation
        )

    def add_message(self, role: str, content: str):
        self.conversation.add(role, content)
        self.conversation.save()

    def apply_memory_update(self, raw_response: str) -> str:
        clean_text, memories, updates, summary = self.parser.parse_extended(raw_response)

        for mem in memories:
            key = mem.get("key", "")
            value = mem.get("value")
            source = "对话"
            confidence = mem.get("confidence", 0.8)
            self.facts.add(key, value, source=source, confidence=confidence)

        for update in updates:
            target = update.get("target", "")
            field = update.get("field", "")
            value = update.get("value")
            add_value = update.get("add")

            if target == "pet_profile":
                profile = self.pet_profile
            elif target == "user_profile":
                profile = self.user_profile
            else:
                continue

            if add_value:
                profile.add_to_list(field, add_value)
            elif value is not None:
                profile.set(field, value)

        if summary:
            self.conversation.set_summary(summary)
            self.conversation.save()

        return clean_text

    def get_pet_profile(self) -> PetProfile:
        return self.pet_profile

    def get_user_profile(self) -> UserProfile:
        return self.user_profile