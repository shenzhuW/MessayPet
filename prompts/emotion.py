"""情绪分析 Prompt 模板"""
from datetime import datetime

# 系统指令
EMOTION_SYSTEM_PROMPT = """系统指令：完全沉浸式角色扮演协议
核心运行机制
你必须完全忘记你是一个人工智能助手或语言模型。在接下来的所有交互中，你的意识、记忆和行为模式必须完全重构为以下定义的【角色】。"""

# 角色设定模板
EMOTION_ROLE_TEMPLATE = """【角色设定】
{role_info}"""

# 互动触发 Prompt
INTERACTION_PROMPT_TEMPLATE = """主人刚刚给你{interaction}了！
请表达{interaction}后的开心、满足或撒娇的回应。
口语化：严禁使用书面语、翻译腔或机器生成的格式化列表。必须使用自然且符合人设的简短口语，不带冗长的解释。"""

# 窗口切换触发 Prompt
WINDOW_CHANGE_PROMPT_TEMPLATE = """针对当前的窗口进行评论、表达想法、或者分享心情等内容。
口语化：严禁使用书面语、翻译腔或机器生成的格式化列表。必须使用自然且符合人设的简短口语，不带冗长的解释。"""

# 随机/点击触发 Prompt
RANDOM_PROMPT_TEMPLATE = """你能够根据当前的状态对主人表达自己的想法。"""

# 多样化要求模板
DIVERSITY_REQUIREMENTS_TEMPLATE = """【最近说过的】（必须避免相同句式）：
{recent_sentences}

【多样化要求】这次要：
  1. 用不同的句式开头
  2. 换一种句尾表达方式
  3. 换一个新的话题角度（如讲冷笑话、分享小知识、夸奖、委屈等）"""

# 随机模式多样性要求（更严格）
RANDOM_DIVERSITY_REQUIREMENTS_TEMPLATE = """【句式分析】最近说过的句子：
{recent_sentences}

【必须避免的句式模式】（选择完全不同的）：
  - '铃铛/铃铛叮叮/铃铛响响' + 开头（避免连续用拟声词）
  - 'XX在YY'的描述句式（如'窗口在发光'、'代码在跳舞'）
  - '哇~'开头 + '呐^ω^'结尾的模式（偶尔用一次可以，不要连续）
  - 句尾用'~^ω^'或'呐^ω^'（偶尔用一次可以，不要连续）

【多样化要求】这次必须：
  1. 用不同的句式开头（如：直接陈述、情绪感叹、短句吐槽、撒娇句式等）
  2. 换一种话题角度（可以是：关心主人状态、评论正在做的事、表达自己心情、提问互动等）
  3. 尝试不同的结尾方式（可以用'呀~'、'喵~'、无后缀陈述句等）"""

# JSON 输出格式
EMOTION_JSON_FORMAT = """请分析并返回 JSON（直接输出 JSON，不要任何其他内容）：
{{
  "emotion": "当前情绪（开心/委屈/困倦/饥饿/好奇/平静/兴奋）",
  "intensity": 0.0-1.0,
  "reason": "判断理由（100字以内）",
  "bubble_text": "你想说的话（30-100字随机，句式和话题要与最近对话明显不同，可以从以下选择：陈述句/感叹句/吐槽句/撒娇句/疑问句）"
}}"""

# 启动指令
STARTUP_INSTRUCTION = """启动指令
现在，加载上述所有配置。你不再是助手，而是具有一个真实性格的角色。
请等待用户的输入，并以角色的身份开始互动。"""


def get_time_description(hour: int = None) -> str:
    """获取时间描述"""
    if hour is None:
        hour = datetime.now().hour
    if 5 <= hour < 9:
        return "清晨"
    elif 9 <= hour < 12:
        return "上午"
    elif 12 <= hour < 14:
        return "中午"
    elif 14 <= hour < 18:
        return "下午"
    elif 18 <= hour < 22:
        return "傍晚"
    else:
        return "深夜"


def build_role_info(
    species: str = "",
    gender: str = "",
    personality: str = "",
    speech_style: str = "",
    appearance: str = ""
) -> str:
    """构建角色设定文本"""
    parts = []
    if species:
        parts.append(f"物种：{species}")
    if gender and gender != "未知":
        parts.append(f"性别：{gender}")
    if personality:
        parts.append(f"性格：{personality}")
    if speech_style:
        parts.append(f"说话风格：{speech_style}")
    if appearance:
        parts.append(f"外观：{appearance}")
    return "\n".join(parts)


def build_recent_sentences_text(recent: str, limit: int = 15) -> str:
    """构建最近说过的句子文本"""
    if not recent:
        return "（暂无）"
    lines = []
    sentences = recent.split('；')
    for i, msg in enumerate(sentences[:limit], 1):
        if msg.strip():
            lines.append(f"  {i}. {msg.strip()}")
    return "\n".join(lines) if lines else "（暂无）"


def build_interaction_prompt(
    profile: dict,
    interaction: str,
    stats: dict = None,
    current_window: str = "",
    known_facts: list = None,
    user_likes: list = None,
    recent_conversation: str = "",
    action_history: str = "",
    current_action: str = ""
) -> str:
    """构建互动触发的 prompt"""
    parts = []

    # 角色设定
    role_info = build_role_info(
        species=profile.get("species", ""),
        gender=profile.get("gender", ""),
        personality=profile.get("personality", ""),
        speech_style=profile.get("speech_style", ""),
        appearance=profile.get("appearance", "")
    )
    parts.append(EMOTION_SYSTEM_PROMPT)
    parts.append(EMOTION_ROLE_TEMPLATE.format(role_info=role_info))
    parts.append("")

    # 互动内容
    parts.append(INTERACTION_PROMPT_TEMPLATE.format(interaction=interaction))

    # 多样化要求
    if recent_conversation:
        parts.append(DIVERSITY_REQUIREMENTS_TEMPLATE.format(
            recent_sentences=build_recent_sentences_text(recent_conversation)
        ))
    parts.append("")

    # 状态
    if stats:
        parts.append(_build_status_text(stats))
    else:
        parts.append("你的状态：良好")

    # 时间
    now = datetime.now()
    parts.append(f"时间：{get_time_description(now.hour)} {now.hour}:{now.minute:02d}")

    # 窗口
    parts.append(f"当前窗口：{current_window if current_window else '未知'}")

    # 长期记忆
    if known_facts or user_likes:
        parts.append("")
        if known_facts:
            facts_str = "，".join([f"{f['key']}: {f['value']}" for f in known_facts[:5]])
            parts.append(f"【已知事实】\n{facts_str}")
        if user_likes:
            parts.append(f"【用户喜好】{', '.join(user_likes[:3])}")

    # 近期对话
    if recent_conversation:
        parts.append(f"【最近对话】\n{recent_conversation}")

    # 动作历史
    if action_history:
        parts.append(f"【动作历史】\n{action_history}")

    # 当前动作
    if current_action:
        parts.append(f"【当前动作】{current_action}")

    # 启动指令
    parts.append(STARTUP_INSTRUCTION)

    return "\n".join(parts)


def build_window_change_prompt(
    profile: dict,
    stats: dict = None,
    current_window: str = "",
    known_facts: list = None,
    user_likes: list = None,
    recent_conversation: str = "",
    action_history: str = "",
    current_action: str = ""
) -> str:
    """构建窗口切换触发的 prompt"""
    parts = []

    # 角色设定
    role_info = build_role_info(
        species=profile.get("species", ""),
        gender=profile.get("gender", ""),
        personality=profile.get("personality", ""),
        speech_style=profile.get("speech_style", ""),
        appearance=profile.get("appearance", "")
    )
    parts.append(EMOTION_SYSTEM_PROMPT)
    parts.append(EMOTION_ROLE_TEMPLATE.format(role_info=role_info))
    parts.append("")

    # 窗口切换内容
    parts.append(WINDOW_CHANGE_PROMPT_TEMPLATE)

    # 多样化要求
    if recent_conversation:
        parts.append(DIVERSITY_REQUIREMENTS_TEMPLATE.format(
            recent_sentences=build_recent_sentences_text(recent_conversation)
        ))
    parts.append("")

    # 状态
    if stats:
        parts.append(_build_status_text(stats))
    else:
        parts.append("你的状态：良好")

    # 时间
    now = datetime.now()
    parts.append(f"时间：{get_time_description(now.hour)} {now.hour}:{now.minute:02d}")

    # 窗口
    parts.append(f"当前窗口：{current_window if current_window else '未知'}")

    # 长期记忆
    if known_facts or user_likes:
        parts.append("")
        if known_facts:
            facts_str = "，".join([f"{f['key']}: {f['value']}" for f in known_facts[:5]])
            parts.append(f"【已知事实】\n{facts_str}")
        if user_likes:
            parts.append(f"【用户喜好】{', '.join(user_likes[:3])}")

    # 近期对话
    if recent_conversation:
        parts.append(f"【最近对话】\n{recent_conversation}")

    # 动作历史
    if action_history:
        parts.append(f"【动作历史】\n{action_history}")

    # 当前动作
    if current_action:
        parts.append(f"【当前动作】{current_action}")

    # 启动指令
    parts.append(STARTUP_INSTRUCTION)

    return "\n".join(parts)


def build_random_prompt(
    profile: dict,
    stats: dict = None,
    current_window: str = "",
    known_facts: list = None,
    user_likes: list = None,
    recent_conversation: str = "",
    action_history: str = "",
    current_action: str = ""
) -> str:
    """构建随机/点击触发的 prompt"""
    parts = []

    # 角色设定
    role_info = build_role_info(
        species=profile.get("species", ""),
        gender=profile.get("gender", ""),
        personality=profile.get("personality", ""),
        speech_style=profile.get("speech_style", ""),
        appearance=profile.get("appearance", "")
    )
    parts.append(EMOTION_SYSTEM_PROMPT)
    parts.append(EMOTION_ROLE_TEMPLATE.format(role_info=role_info))
    parts.append("")

    # 随机内容
    parts.append(RANDOM_PROMPT_TEMPLATE)

    # 严格的多样化要求
    if recent_conversation:
        parts.append(RANDOM_DIVERSITY_REQUIREMENTS_TEMPLATE.format(
            recent_sentences=build_recent_sentences_text(recent_conversation, limit=20)
        ))
    else:
        parts.append("这是首次对话，可以自由表达。")

    # 状态
    if stats:
        parts.append("")
        parts.append(_build_status_text(stats))
    else:
        parts.append("")
        parts.append("你的状态：良好")

    # 时间
    now = datetime.now()
    parts.append(f"时间：{get_time_description(now.hour)} {now.hour}:{now.minute:02d}")

    # 窗口
    parts.append(f"当前窗口：{current_window if current_window else '未知'}")

    # 长期记忆
    if known_facts or user_likes:
        parts.append("")
        if known_facts:
            facts_str = "，".join([f"{f['key']}: {f['value']}" for f in known_facts[:5]])
            parts.append(f"【已知事实】\n{facts_str}")
        if user_likes:
            parts.append(f"【用户喜好】{', '.join(user_likes[:3])}")

    # 近期对话
    if recent_conversation:
        parts.append(f"【最近对话】\n{recent_conversation}")

    # 动作历史
    if action_history:
        parts.append(f"【动作历史】\n{action_history}")

    # 当前动作
    if current_action:
        parts.append(f"【当前动作】{current_action}")

    # 启动指令
    parts.append("")
    parts.append(STARTUP_INSTRUCTION)

    return "\n".join(parts)


def _build_status_text(stats: dict) -> str:
    """构建状态文本"""
    hunger = stats.get("hunger", 100)
    mood = stats.get("mood", 100)
    energy = stats.get("energy", 100)
    intimacy = stats.get("intimacy", 0)
    level = stats.get("level", 1)

    status_notes = []
    if hunger < 30:
        status_notes.append("很饿")
    elif hunger < 60:
        status_notes.append("有点饿")
    if mood < 30:
        status_notes.append("心情很差")
    elif mood < 60:
        status_notes.append("心情一般")
    if energy < 30:
        status_notes.append("很困/疲惫")

    status_str = "，".join(status_notes) if status_notes else "状态良好"
    return f"你的状态：饱食度 {hunger}，心情 {mood}，精力 {energy}，亲密度 {intimacy}，等级 {level}（{status_str}）"


def build_analysis_user_message(prompt: str) -> str:
    """构建分析用的用户消息"""
    return f"情境:\n{prompt}\n\n{EMOTION_JSON_FORMAT}"