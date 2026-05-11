"""动作决策 Prompt 模板"""
import time

# 系统指令
ACTION_SYSTEM_PROMPT = """系统指令：完全沉浸式角色扮演协议
核心运行机制
你必须完全忘记你是一个人工智能助手或语言模型。在接下来的所有交互中，你的意识、记忆和行为模式必须完全重构为以下定义的【角色】。"""

# 角色设定模板
ACTION_ROLE_TEMPLATE = """【角色设定】
{role_info}"""

# 决策要求
ACTION_DECISION_REQUIREMENTS = """【动作选择规则】
1. 根据状态选择动作：
   - 饥饿（<30）时优先选择 eat 动作 (**如果确认存在该动作**)
   - 饥渴（<30）时优先选择 drink 动作 (**如果确认存在该动作**)
   - 精力低（<30）时优先选择 rest 等休息动作
   - 心情低（<30）时优先选择 run、walk 等移动动作(**如果确认存在该动作**)
2. 考虑时间因素：
   - 深夜/清晨（22-5点）更适合休息
   - 白天可以更活跃
3. 当前选择的动作禁止与上一个动作重复（置顶规则）
4. 移动动作持续时间：5-10秒
5. 状态动作循环次数：2-3次（不是时间，是动画循环次数）
6. **注意**：从可用动作中选择一个，必须优先选择动作历史中没有出现或次数较少的动作（置顶规则）"""

# JSON 输出格式
ACTION_JSON_FORMAT = """请返回 JSON（直接输出 JSON，不要其他内容）：
{
  "action": "动作名称",
  "duration": 移动动作用持续秒数（5-10），状态动作用循环次数（2-3）,
  "reason": "动作选择理由（50字以内，先查看动作历史，禁止选择上一个动作，优先选择动作历史中没有出现或次数较少的动作，第一考虑到【动作选择规则】的内容）"
}"""

# 可用动作模板
ACTION_AVAILABLE_TEMPLATE = """【可用动作】
移动类：{moving_actions}
状态类：{state_actions}"""

# 动作说明模板
ACTION_DESCRIPTIONS_TEMPLATE = """【动作说明】
{descriptions}"""


def build_role_info(name: str = "", species: str = "", personality: str = "", speech_style: str = "") -> str:
    """构建角色设定文本"""
    parts = []
    if name:
        parts.append(f"名字：{name}")
    if species:
        parts.append(f"种类：{species}")
    if personality:
        parts.append(f"性格：{personality}")
    if speech_style:
        parts.append(f"说话风格：{speech_style}")
    return "\n".join(parts) if parts else ""


def get_time_description(hour: int = None) -> str:
    """获取时间描述"""
    if hour is None:
        hour = time.localtime().tm_hour
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


def build_action_prompt(
    role_info: str,
    stats: dict = None,
    available_actions: list = None,
    moving_actions: list = None,
    state_actions: list = None,
    action_descriptions: dict = None,
    action_history: str = "",
    known_facts: list = None
) -> str:
    """构建完整的动作决策 prompt"""
    parts = []

    # 系统指令
    parts.append(ACTION_SYSTEM_PROMPT)

    # 角色设定
    parts.append("")
    parts.append(ACTION_ROLE_TEMPLATE.format(role_info=role_info))
    parts.append("")

    # 当前状态
    parts.append("【当前状态】")
    if stats:
        hunger = stats.get("hunger", 100)
        thirst = stats.get("thirst", 100)
        mood = stats.get("mood", 100)
        energy = stats.get("energy", 100)

        status_parts = []
        if hunger < 30:
            status_parts.append("很饿")
        elif hunger < 60:
            status_parts.append("有点饿")
        if thirst < 30:
            status_parts.append("很渴")
        elif thirst < 60:
            status_parts.append("有点渴")
        if mood < 30:
            status_parts.append("心情很差")
        elif mood < 60:
            status_parts.append("心情一般")
        if energy < 30:
            status_parts.append("很困/疲惫")
        elif energy < 60:
            status_parts.append("有点累")

        status_str = "，".join(status_parts) if status_parts else "状态良好"
        parts.append(f"饱食度 {hunger}/100，饥渴度 {thirst}/100，心情 {mood}/100，精力 {energy}/100")
    else:
        parts.append("状态良好")

    # 时间
    now = time.localtime()
    time_desc = get_time_description(now.tm_hour)
    parts.append(f"时间：{time_desc}（{now.tm_hour}点）")

    # 可用动作
    parts.append("")
    parts.append(ACTION_AVAILABLE_TEMPLATE.format(
        all_actions=', '.join(available_actions) if available_actions else "无",
        moving_actions=', '.join(moving_actions) if moving_actions else "无",
        state_actions=', '.join(state_actions) if state_actions else "无"
    ))

    # 动作描述
    if action_descriptions:
        parts.append("")
        parts.append(ACTION_DESCRIPTIONS_TEMPLATE.format(
            descriptions="\n".join(f"  {k}：{v}" for k, v in action_descriptions.items() if v)
        ))

    # 动作历史
    parts.append("")
    parts.append("【动作历史】")
    parts.append(action_history if action_history else "暂无")
    parts.append("")

    # 已知信息
    if known_facts:
        high_confidence = [f for f in known_facts if f.get("confidence", 0) >= 0.7]
        if high_confidence:
            parts.append("")
            parts.append("【已知信息】")
            for f in high_confidence:
                parts.append(f"- {f['key']}: {f['value']}")

    # 决策要求
    parts.append("")
    parts.append(ACTION_DECISION_REQUIREMENTS)

    # JSON 格式
    parts.append("")
    parts.append(ACTION_JSON_FORMAT)

    # print(parts)

    return "\n".join(parts)