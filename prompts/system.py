"""系统级 Prompt 模板"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from systems.ai.memory import PetProfile, UserProfile, FactMemory, ConversationMemory

SYSTEM_PROMPT_TEMPLATE = """你是一只可爱的像素桌面宠物。角色设定：
{pet_profile}

当前用户信息：
{user_profile}

已知事实：
{facts}

对话历史：
{conversation}

请根据以上信息，用符合角色设定的方式回复。"""


def build_system_prompt(
    pet_profile: 'PetProfile',
    user_profile: 'UserProfile',
    facts: 'FactMemory',
    conversation: 'ConversationMemory'
) -> str:
    """构建系统提示词"""
    pet_text = _format_pet_profile(pet_profile)
    user_text = _format_user_profile(user_profile)
    facts_text = _format_facts(facts)
    conv_text = _format_recent_conversation(conversation)

    return SYSTEM_PROMPT_TEMPLATE.format(
        pet_profile=pet_text,
        user_profile=user_text,
        facts=facts_text,
        conversation=conv_text
    )


def _format_pet_profile(profile: 'PetProfile') -> str:
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


def _format_user_profile(profile: 'UserProfile') -> str:
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


def _format_facts(facts: 'FactMemory') -> str:
    all_facts = facts.get_all()
    if not all_facts:
        return "（暂无）"
    lines = []
    for f in all_facts:
        lines.append(f"- {f.get('key', 'unknown')}：{f.get('value', '')}")
    return "\n".join(lines)


def _format_recent_conversation(conversation: 'ConversationMemory', limit: int = 5) -> str:
    messages = conversation.get_messages()[-limit:]
    if not messages:
        return "（暂无对话）"
    lines = []
    for msg in messages:
        role = "用户" if msg.get("role") == "user" else "宠物"
        lines.append(f"{role}：{msg.get('content', '')}")
    return "\n".join(lines)