# systems/ai/context_builder.py
from typing import List, Dict, Optional
from prompts.system import SYSTEM_PROMPT_TEMPLATE
from systems.ai.memory import ConversationMemory, FactMemory, UserProfile, PetProfile

class ContextBuilder:
    # SYSTEM_PROMPT_TEMPLATE is now imported from prompts.system

    def __init__(self, max_context_messages: int = 30):
        self.max_context_messages = max_context_messages

    def build(
        self,
        pet_profile: PetProfile,
        user_profile: UserProfile,
        facts: FactMemory,
        conversation: ConversationMemory
    ) -> List[Dict]:
        messages = []

        system_content = self._build_system_prompt(pet_profile, user_profile, facts, conversation)
        messages.append({"role": "system", "content": system_content})

        conversation_messages = conversation.get_messages()
        if conversation.summary and len(conversation_messages) > 10:
            messages.append({
                "role": "system",
                "content": f"[对话摘要] {conversation.summary}"
            })

        recent_messages = conversation_messages[-self.max_context_messages:]
        for msg in recent_messages:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        return messages

    def _build_system_prompt(
        self,
        pet_profile: PetProfile,
        user_profile: UserProfile,
        facts: FactMemory,
        conversation: ConversationMemory
    ) -> str:
        pet_text = self._format_pet_profile(pet_profile)
        user_text = self._format_user_profile(user_profile)
        facts_text = self._format_facts(facts)
        conv_text = self._format_recent_conversation(conversation)

        return SYSTEM_PROMPT_TEMPLATE.format(
            pet_profile=pet_text,
            user_profile=user_text,
            facts=facts_text,
            conversation=conv_text
        )

    def _format_pet_profile(self, profile: PetProfile) -> str:
        data = profile.get_all()
        lines = [f"名字：{data.get('name', '')}"]
        if data.get('species'):
            lines.append(f"种类：{data['species']}")
        if data.get('personality'):
            lines.append(f"性格：{data['personality']}")
        if data.get('appearance'):
            lines.append(f"外观：{data['appearance']}")
        if data.get('speech_style'):
            lines.append(f"说话风格：{data['speech_style']}")
        return "\n".join(lines)

    def _format_user_profile(self, profile: UserProfile) -> str:
        data = profile.get_all()
        lines = []
        if data.get('name'):
            lines.append(f"名字：{data['name']}")
        if data.get('relationship'):
            lines.append(f"关系：{data['relationship']}")
        prefs = data.get('preferences', [])
        if prefs:
            lines.append(f"喜好：{', '.join(prefs)}")
        if not lines:
            lines.append("（未知）")
        return "\n".join(lines)

    def _format_facts(self, facts: FactMemory) -> str:
        all_facts = facts.get_all()
        if not all_facts:
            return "（暂无）"
        lines = []
        for f in all_facts:
            lines.append(f"- {f.get('key', 'unknown')}：{f.get('value', '')}")
        return "\n".join(lines)

    def _format_recent_conversation(self, conversation: ConversationMemory, limit: int = 5) -> str:
        messages = conversation.get_messages()[-limit:]
        if not messages:
            return "（暂无对话）"
        lines = []
        for msg in messages:
            role = "用户" if msg.get("role") == "user" else "宠物"
            lines.append(f"{role}：{msg.get('content', '')}")
        return "\n".join(lines)