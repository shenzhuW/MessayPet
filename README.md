# MessayPet - 桌面宠物小助手

一款基于 AI 的桌面宠物软件。宠物可以与claude code进行联动。汇报后台claude code的任务状态，并进行提醒。拥有智能记忆、情绪系统和行为决策能力，会在桌面上自由移动、和你互动，并根据你的工作状态做出自然的反应。

## 功能概览

### 基础交互
- **左键单击** - 与宠物互动
- **左键双击** - 打开聊天窗口（任务栏有图标）
- **右键单击** - 打开右键菜单
- **拖拽移动** - 拖动宠物到任意位置

---

## 新手入门

### 1. 安装运行

```bash
# 克隆项目
git clone https://github.com/yourusername/deskpet.git
cd deskpet

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

首次运行后，会在用户目录 `~/.deskpet/` 下创建以下文件：
- `data/config.json` - 主配置文件
- `data/stats.json` - 宠物状态数据
- `skins/` - 皮肤文件夹

### 2. 配置 AI

程序需要连接 LLM API 才能正常工作。右键宠物 → 设置 → 配置 API。

**气泡 AI**：用于生成情绪分析和气泡文字
**宠物聊天 AI**：用于宠物对话功能

支持 OpenAI 兼容接口。详细配置请参考 [CONFIG.md](CONFIG.md)。

> ⚠️ **注意**：气泡 API 需要关闭思考模式（thinking）。

### 3. 右键菜单功能

右键点击宠物打开菜单：

**属性**
- 查看饱食度、心情、健康、活力、年龄
- 进度条实时显示数值

**互动**
- 🍎 喂食 - 增加饱食度
- 🎮 玩耍 - 增加心情，获得经验
- 💤 休息 - 恢复精力

**功能**
- 📊 工时统计 - 打开工作时长统计页面
- 🌐 快速打开 - 一键打开常用网页（需在设置中配置）

**编辑角色卡**
- 编辑宠物档案（名字、性格、外貌等）
- 编辑主人信息（名字、喜好等）

**设置**
- API 配置
- 皮肤切换
- 动作速度设置

---

## 核心功能详解

### 宠物养成系统

宠物有多种属性需要照顾：

| 属性 | 说明 | 衰减速度 | 恢复方式 |
|------|------|----------|----------|
| 饱食度 | 饥饿时影响健康 | 约6小时衰减至0 | 喂食 +20 |
| 心情 | 影响活力 | 约5小时衰减至0 | 玩耍 +15 |
| 精力 | 决定动作选择 | 约6小时衰减至0 | 休息 +30 |
| 饥渴度 | 饥渴时影响健康 | 约5小时衰减至0 | 喝水 +20 |
| 健康 | 综合状态 | 饱食度/心情 <30 时下降 | 喂食/休息恢复 |
| 亲密度 | 互动积累 | 不衰减 | 互动 +5~15 |
| 经验值 | 升级用 | 不衰减 | 互动 +5~10 |
| 年龄 | 真实天数 | 不衰减 | 自动计算 |

**属性状态影响**：
- 饥饿时（<30）→ 优先选择 eat 动作
- 精力低（<30）→ 优先选择 rest 动作
- 心情低（<30）→ 优先选择 run 等活跃动作

---

### AI 智能系统

#### 情绪分析 + 气泡系统

宠物会根据当前状态和上下文实时分析情绪，生成气泡文字：

- **7种情绪状态**：开心、委屈、困倦、饥饿、好奇、平静、兴奋
- **情绪影响动画**：激动时动画加速，困倦时动画减速
- **多样化回复**：自动避免重复句式，保持对话新鲜感

#### 动作决策

宠物会智能选择动作：
- 根据当前属性状态选择（饿了找吃的、累了休息）
- 考虑时间因素（夜间更安静）
- 避免连续重复动作
- 基于配置中的动作自主选择

#### 自主性格设置

宠物性格通过"编辑角色卡"中的"性格"字段自定义设置。不同的性格描述会影响宠物的回复风格。

例如：
- "活泼好奇、有点话痨、爱撒娇" - 活泼型
- "高冷话少，偶尔傲娇" - 高冷型
- "温柔体贴，善于倾听" - 温柔型

---

### 记忆系统

宠物有完善的记忆系统：

#### 1. 对话记忆
- 保留最近 3 天的对话内容
- 用于理解上下文，生成更自然的回复
- 自动清理过期对话

#### 2. 事实记忆
- 记录关于主人的重要信息
- 例如："主人喜欢在下午喝咖啡"
- 支持手动编辑和自动学习

#### 3. 用户画像
- 主人姓名、昵称
- 喜好、习惯
- 关系设定

#### 4. 宠物档案
- 名字、性别、物种
- 性格、外貌、背景
- 语言风格、喜欢/讨厌的事物
- 可在"编辑角色卡"中修改

---

### 工作状态感知

宠物会监控当前前台窗口，根据你使用的应用做出反应：

- 检测工作应用（IDE、浏览器、文档编辑器等）
- 记录各应用使用时长
- 宠物会根据你工作的内容做出评论

### Claude Code 任务联动

宠物与 Claude Code 集成，实时监控任务状态：

- **中断提醒**：当 Claude Code 遇到需要人工介入的情况（如等待确认、权限请求、错误需处理）时，宠物会通过气泡及时提醒你
- **任务完成**：Claude Code 任务执行完毕后，宠物会发出气泡通知

#### 配置方法

**步骤 1：复制 hook 脚本**

将项目中的 `hooks/hooks_notification.py` 复制到 Claude Code 配置目录：
```bash
cp hooks/hooks_notification.py ~/.claude/
```

**步骤 2：配置 Claude Code hooks**

在 Claude Code 全局配置 `~/.claude/settings.json` 中添加：

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "python C:/Users/<你的用户名>/.claude/hooks_notification.py"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python C:/Users/<你的用户名>/.claude/hooks_notification.py"
      }]
    }],
    "PermissionRequest": [{
      "hooks": [{
        "type": "command",
        "command": "python C:/Users/<你的用户名>/.claude/hooks_notification.py"
      }]
    }]
  }
}
```

**常用 hook 类型**：
- `PermissionRequest` - 需要授权时（如执行命令、写文件前）
- `Stop` - Claude Code 任务结束
- `UserPromptSubmit` - 用户提交新任务时

---

### 工时统计

右键 → 功能 → 工时统计，打开可视化统计页面：

**功能**：
- 查看今日/本周/本月工时
- 按项目分组统计
- 时间线视图
- 周趋势图
- 每日详细记录表

数据自动记录在 `~/.deskpet/data/work_records.json`，保留最近 30 天。

---

### 快速打开网页

在设置中配置常用网页快捷方式，右键 → 功能 → 快速打开 即可一键访问。

例如配置：
- GitHub
- 邮箱
- 工作后台

---

### 聊天功能

双击宠物打开聊天窗口：

- 与宠物进行自然对话
- 支持 Markdown 渲染
- 可切换 AI 提供商（内网 API / Claude Code）
- 对话内容自动保存（最近3天，最多30条）
- **智能记忆**：宠物会从对话中学习，自动更新用户画像和事实记忆

---

### 皮肤系统

支持自定义皮肤，每个皮肤包含：
- 各动作的 PNG 帧动画（idle、walk、run、eat 等）
- 配置文件（动作列表、动作描述）

内置皮肤：
- `default` - 默认像素宠物（吃、喝、休息、开心等动作）
- `nakaji` - 另一个可爱风格皮肤

**切换皮肤**：右键 → 设置 → 皮肤选择

#### 创建自定义皮肤

**目录结构**：
```
skins/
└── my_skin/           # 皮肤文件夹名称
    ├── config.json    # 皮肤配置
    ├── idle/          # 待机动作
    │   ├── idle_000.png
    │   ├── idle_001.png
    │   └── ...
    ├── walk/          # 行走动作
    │   ├── walk_000.png
    │   └── ...
    └── ...
```

**配置文件说明** (`config.json`)：

```json
{
  "name": "我的皮肤名称",
  "description": "皮肤描述",
  "frame_size": [64, 64],
  "moving_actions": ["walk", "run"],
  "state_actions": ["idle", "eat", "drink", "rest", "happy"],
  "passive_actions": ["fall", "land", "held", "interact"],
  "action_descriptions": {
    "walk": "四处走动探索",
    "run": "快速奔跑",
    "idle": "原地休息，待机状态",
    "eat": "吃东西",
    "drink": "喝水",
    "rest": "休息",
    "happy": "开心玩耍",
    "fall": "下落动画",
    "land": "落地动画",
    "held": "被抓住动画",
    "interact": "互动动画"
  }
}
```

**配置项说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 皮肤显示名称 |
| `description` | string | 否 | 皮肤描述 |
| `frame_size` | array | 是 | 帧图片尺寸 [宽, 高]，如 `[64, 64]` |
| `moving_actions` | array | 是 | 移动类动作（宠物自主选择） |
| `state_actions` | array | 是 | 状态类动作（宠物自主选择） |
| `passive_actions` | array | 是 | 被动动作（被触发时播放） |
| `action_descriptions` | object | 否 | 动作描述（用于 AI 决策参考） |

> ⚠️ **必须包含的动作**：`passive_actions` 中必须包含以下四个动作，否则宠物可能出现异常：
> - `idle` - 待机动画（无动作时循环播放）
> - `held` - 被抓动画（拖拽宠物时播放）
> - `fall` - 下落动画（宠物掉落时播放）
> - `land` - 落地动画（宠物落地时播放）

**帧动画命名规则**：
- 文件名格式：`动作名_序号.png`
- 序号从 0 开始，如 `idle_000.png`, `idle_001.png`
- 支持 PNG 格式，建议透明背景

**动作类型**：

| 类型 | 说明 | 示例 |
|------|------|------|
| `moving_actions` | 宠物移动时播放 | walk, run |
| `state_actions` | 宠物状态动画 | idle, happy, eat |
| `passive_actions` | 被外界触发 | fall（掉落）, land（落地）, held（被抓） |

**安装皮肤**：
1. 将皮肤文件夹放入 `~/.deskpet/skins/` 目录
2. 重启程序
3. 右键 → 设置 → 选择新皮肤

---

## 项目结构

```
DeskPet/
├── main.py                    # 程序入口
├── core/                      # 核心模块
│   ├── pet_window.py          # 宠物主窗口
│   ├── stat_manager.py        # 属性状态管理
│   ├── config_manager.py      # 配置管理
│   ├── emotion.py             # 情绪状态
│   ├── work_tracker.py        # 工时记录
│   └── window_tracker.py      # 窗口监控
├── systems/ai/                # AI 系统
│   ├── llm_client.py          # LLM 客户端
│   ├── memory.py              # 记忆系统
│   ├── emotion_analyzer.py    # 情绪分析
│   └── bubble_personality.py  # 性格系统
├── prompts/                   # AI 提示词
│   ├── emotion.py             # 情绪分析 Prompt
│   └── action.py              # 动作决策 Prompt
├── ui/                        # UI 组件
│   ├── settings_dialog.py     # 设置对话框
│   ├── chat_dialog.py         # 聊天窗口
│   ├── context_menu.py        # 右键菜单
│   └── pet_profile_editor.py  # 角色卡编辑器
├── templates/                 # HTML 模板
│   └── work_stats.html        # 工时统计页面
└── skins/                     # 皮肤资源
    ├── default/
    └── nakaji/
```

---

## 依赖环境

- Python 3.10+
- PySide6 - GUI 框架
- Pillow - 图片处理
- psutil - 系统监控
- 其他依赖见 requirements.txt

---

## 配置文件说明

配置文件位于 `~/.deskpet/data/config.json`，常用配置项：

```json
{
  "llm_config": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "your-key",
    "base_url": "https://api.openai.com/v1",
    "bubble_api_key": "your-key",
    "bubble_base_url": "https://api.openai.com/v1",
    "bubble_model": "gpt-4"
  },
  "web_shortcuts": [
    {"name": "GitHub", "url": "https://github.com"}
  ],
  "current_skin": "default"
}
```

---

## 常见问题

**Q: 程序启动没反应？**
A: 检查 Python 版本（需要 3.10+），确认依赖安装完整。查看终端错误信息。

**Q: 宠物不显示气泡？**
A: 检查 API 配置是否正确，确认网络可以访问 LLM 接口。

**Q: 如何添加自定义皮肤？**
A: 在 `~/.deskpet/skins/` 下创建新文件夹，参考现有皮肤结构放置帧动画图片和 `config.json`。

**Q: 记忆数据在哪？**
A: 位于 `~/.deskpet/data/memory/` 目录下，包括 facts.json、user_profile.json、pet_profile.json。

---
## 皮肤素材致谢

部分皮肤素材来源于 [DyberPet_GenshinImpact](https://github.com/ChaozhongLiu/DyberPet_GenshinImpact)，感谢原作者的贡献。

---

## 许可证

MIT License
