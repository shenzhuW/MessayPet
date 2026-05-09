# ui/chat_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
    QTextEdit, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor, QTextOption
from systems.ai.llm_client import LLMClient, ClaudeCLIClient
from core.config import LLMConfig
from systems.ai.memory import ChatMemory
import asyncio
import threading
import re

PIXEL_FONT = "Microsoft YaHei UI"
PIXEL_BG = "rgba(245, 240, 225, 250)"
PIXEL_BORDER = "#8b6914"
PIXEL_BORDER_DARK = "#5d4037"
PIXEL_TEXT = "#3f2f25"


def _md_to_html(text: str) -> str:
    """将 Markdown 转换为 HTML"""
    # 过滤思考内容
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    try:
        import markdown
        return markdown.markdown(
            text, extensions=["fenced_code", "tables", "nl2br", "sane_lists"]
        )
    except ImportError:
        pass

    # 兜底手动解析
    html, in_code, in_ul = [], False, False
    for raw in text.split("\n"):
        if raw.strip().startswith("```"):
            if in_code:
                html.append("</code></pre>")
            else:
                html.append("<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            html.append(raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue
        line = raw
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"\*(.+?)\*", r"<i>\1</i>", line)
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', line)
        if re.match(r"^#{1,6}\s", line):
            lvl = len(line.split()[0])
            line = f"<h{lvl}>{line[lvl:].strip()}</h{lvl}>"
        elif re.match(r"^-{3,}$|^_{3,}$|^\*{3,}$", line.strip()):
            line = "<hr>"
        elif re.match(r"^\s*[-*+]\s", line):
            content = re.sub(r"^\s*[-*+]\s", "", line)
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            line = f"<li>{content}</li>"
        else:
            if in_ul:
                html.append("</ul>")
                in_ul = False
            line = f"<p>{line}</p>" if line.strip() else ""
        html.append(line)
    if in_code:
        html.append("</code></pre>")
    if in_ul:
        html.append("</ul>")
    return "\n".join(html)

# 聊天窗口专用的 system prompt
CHAT_SYSTEM_PROMPT = """你是一只可爱的像素桌面宠物角色。

角色特点：
- 活泼可爱，偶尔撒娇
- 说话自然，符合角色设定
- 可以评论、分享想法、聊天互动

添加记忆重要规则：
- 若对话中有关键信息（如用户爱好、重要事实），请在回复末尾添加记忆标记
- 若用户提到要修改宠物/用户设定，使用更新标记
- 只有具有长期性记忆的内容才需要添加记忆标记，不具有长期性质的关键信息则不需要记录
- 不是一次性的事务性提示（如：“帮我查一下今天的日期”）
- 用户明确表达了倾向、原则或重要事实（“我喜欢许嵩”）

记忆标记格式：
<MEMORY>{"key": "描述", "value": "具体内容", "confidence": 0.8}</MEMORY>

更新标记格式：
<UPDATE>{"target": "pet_profile|user_profile", "field": "字段名", "value": "新值"}</UPDATE>
<UPDATE>{"target": "user_profile", "field": "preferences", "add": "新增内容"}</UPDATE>"""


def _build_long_term_context(memory_manager) -> str:
    """构建长期记忆上下文"""
    if not memory_manager:
        return ""

    parts = []

    # 宠物资料
    if hasattr(memory_manager, 'pet_profile'):
        profile = memory_manager.pet_profile.get_all()
        if profile.get("name"):
            parts.append(f"宠物名字：{profile['name']}")
        if profile.get("speech_style"):
            parts.append(f"说话风格：{profile['speech_style']}")

    # 用户资料
    if hasattr(memory_manager, 'user_profile'):
        profile = memory_manager.user_profile.get_all()
        if profile.get("name"):
            parts.append(f"用户名字：{profile['name']}")
        if profile.get("nickname"):
            parts.append(f"用户昵称：{profile['nickname']}")
        if profile.get("preferences"):
            prefs = "、".join(profile['preferences'][:5])
            parts.append(f"用户喜好：{prefs}")

    # 已知事实
    if hasattr(memory_manager, 'facts'):
        facts = memory_manager.facts.get_all()
        if facts:
            fact_strs = [f"{f['key']}：{f['value']}" for f in facts]
            if fact_strs:
                parts.append("已知信息：" + "；".join(fact_strs))

    return "【背景信息】" + "\n".join(parts) + "\n" if parts else ""


def filter_thinking(text: str) -> str:
    """过滤掉思考内容（<think>...</think>）"""
    filtered = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    filtered = re.sub(r'\n{3,}', '\n\n', filtered)
    return filtered.strip()


class ChatDialog(QDialog):
    def __init__(self, llm_client, stat_manager=None, parent=None, memory_manager=None):
        super().__init__(parent)
        self._default_client = llm_client  # 保存默认客户端
        self._current_client = llm_client
        self.stat_manager = stat_manager
        self._chat_in_progress = False
        self._response_buffer = ""

        # 聊天窗口独立的短期记忆（3天，最多30条）
        self._chat_memory = ChatMemory()

        # 用于提取长期记忆（可选）
        self._memory_manager = memory_manager

        self.setWindowTitle("和宠物聊天")
        self.setFixedSize(500, 550)
        self.setStyleSheet(f"QDialog {{ background-color: {PIXEL_BG}; }}")

        # 设置窗口图标
        from ui.settings_dialog import create_pixel_icon
        self.setWindowIcon(create_pixel_icon(32, "pet"))

        # 居中显示
        from PySide6.QtGui import QScreen
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            center = screen.geometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)

        self._setup_ui()

        # 添加欢迎消息
        self._add_message("宠物", "嗨！你好呀~ 有什么想和我聊的吗？", is_pet=True)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 聊天记录区域
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont(PIXEL_FONT, 11))
        self.chat_area.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.chat_area.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.chat_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: white;
                border: 3px solid {PIXEL_BORDER};
                color: {PIXEL_TEXT};
                font-family: "{PIXEL_FONT}";
                font-size: 12px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.chat_area)

        # 输入区域
        input_layout = QHBoxLayout()

        self.input_box = QLineEdit()
        self.input_box.setFont(QFont(PIXEL_FONT, 11))
        self.input_box.setPlaceholderText("输入消息...")
        self.input_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                border: 2px solid {PIXEL_BORDER};
                color: {PIXEL_TEXT};
                font-family: "{PIXEL_FONT}";
                font-size: 12px;
                padding: 8px;
            }}
            QLineEdit:focus {{ border-color: {PIXEL_BORDER_DARK}; }}
        """)
        self.input_box.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_box)

        # AI 提供商选择下拉框
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["内网 API", "Claude Code"])
        self.provider_combo.setFont(QFont(PIXEL_FONT, 10))
        self.provider_combo.setFixedWidth(100)
        self.provider_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                border: 2px solid {PIXEL_BORDER};
                color: {PIXEL_TEXT};
                font-family: "{PIXEL_FONT}";
                font-size: 10px;
                padding: 4px 8px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        input_layout.addWidget(self.provider_combo)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFont(QFont(PIXEL_FONT, 11))
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #d4c8a8;
                border: 2px solid {PIXEL_BORDER};
                color: {PIXEL_TEXT};
                font-family: "{PIXEL_FONT}";
                font-size: 12px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{ background-color: #ffcd75; }}
            QPushButton:disabled {{ background-color: #e0d8c8; color: #aaa; }}
        """)
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # 定时器用于更新显示
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)

    def _on_provider_changed(self, index):
        """切换 AI 提供商"""
        if index == 1:  # Claude Code
            config = LLMConfig()
            self._current_client = ClaudeCLIClient(config)
        else:  # 内网 API
            self._current_client = self._default_client

    def _add_message(self, sender: str, text: str, is_pet: bool = False):
        """添加消息到聊天区域"""
        if is_pet:
            text = filter_thinking(text)

        icon = "🐱" if is_pet else "👤"
        color = "#8b6914" if is_pet else "#5d4037"

        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # 添加换行（如果当前不在行首）
        if cursor.position() > 0:
            cursor.insertHtml("<br><br>")

        cursor.insertHtml(f'<b style="color:{color};font-size:14px;">{icon}</b> ')
        cursor.insertHtml(_md_to_html(text))

        self.chat_area.setTextCursor(cursor)
        self.chat_area.ensureCursorVisible()

    def _send_message(self):
        """发送消息"""
        text = self.input_box.text().strip()
        if not text or self._chat_in_progress:
            return

        self._chat_in_progress = True
        self._response_buffer = ""
        self.input_box.clear()
        self.send_btn.setEnabled(False)

        # 显示用户消息
        self._add_message("我", text, is_pet=False)

        # 添加宠物消息占位符（带图标）
        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml("<br><br>")
        cursor.insertHtml('<b style="color:#8b6914;font-size:14px;">🐱</b> ')
        self._pet_msg_start = cursor.position()  # 记录宠物消息开始位置
        self._pet_msg_html = '<b style="color:#8b6914;font-size:14px;">🐱</b> '  # 初始 HTML
        self.chat_area.setTextCursor(cursor)

        # 异步流式接收
        self._stream_response(text)

    def _update_display(self):
        """定时更新显示（主线程安全）"""
        if not self._response_buffer:
            return

        # 取出缓冲区的文本
        text_to_show = self._response_buffer
        self._response_buffer = ""

        # 流式显示：使用纯文本追加，结束时整体渲染 Markdown
        filtered = filter_thinking(text_to_show)
        if filtered:
            cursor = self.chat_area.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(filtered)
            self.chat_area.setTextCursor(cursor)
            self.chat_area.ensureCursorVisible()

        # 如果聊天完成
        if not self._chat_in_progress:
            self._update_timer.stop()
            self._finish_response()

    def _finish_response(self):
        """结束响应，重新渲染宠物消息的 Markdown"""
        if hasattr(self, '_last_response') and self._last_response:
            clean_response = filter_thinking(self._last_response)

            # 重新渲染宠物消息（Markdown）
            if hasattr(self, '_pet_msg_start'):
                cursor = self.chat_area.textCursor()
                cursor.setPosition(self._pet_msg_start)
                cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                cursor.insertHtml(self._pet_msg_html + _md_to_html(clean_response))

            # 提取长期记忆
            if self._memory_manager and hasattr(self._memory_manager, 'apply_memory_update'):
                self._memory_manager.apply_memory_update(self._last_response)

            # 也添加到聊天短期记忆
            self._chat_memory.add("assistant", clean_response)

        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml("<br><br>")
        self.chat_area.setTextCursor(cursor)
        self.chat_area.ensureCursorVisible()
        self.send_btn.setEnabled(True)

    def _stream_response(self, user_message: str):
        """流式接收响应 - 使用独立的聊天短期记忆"""
        # 添加到聊天短期记忆
        self._chat_memory.add("user", user_message)

        # 构建长期记忆上下文
        long_term_context = _build_long_term_context(self._memory_manager)

        # 设置 system prompt，包含长期记忆
        self._current_client.config.system_prompt = CHAT_SYSTEM_PROMPT
        if long_term_context:
            self._current_client.config.system_prompt += "\n\n" + long_term_context

        # 清空客户端历史，用聊天窗口的独立历史（最近30条）
        self._current_client.clear_history()
        for msg in self._chat_memory.get_recent(limit=30):
            self._current_client.add_message(msg["role"], msg["content"])

        self._last_response = ""

        def run_async():
            async def run():
                try:
                    async for chunk in self._current_client.chat(user_message):
                        self._response_buffer += chunk
                        self._last_response += chunk
                except Exception as e:
                    self._response_buffer += f"\n\n[错误: {str(e)}]"
                    self._last_response += f"\n\n[错误: {str(e)}]"
                finally:
                    # 标记聊天完成
                    self._chat_in_progress = False
                    # 确保最后一次更新
                    QTimer.singleShot(100, lambda: self._update_display())

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run())
            except Exception as e:
                self._response_buffer += f"\n\n[错误: {str(e)}]"
                self._last_response += f"\n\n[错误: {str(e)}]"
                self._chat_in_progress = False
            finally:
                loop.close()

        # 启动定时器定期更新显示
        self._update_timer.start(100)

        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()