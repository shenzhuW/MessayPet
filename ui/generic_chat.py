# ui/generic_chat.py
"""GenericAgent 任务执行聊天窗口"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QSplitter, QWidget, QLabel
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor, QPalette, QColor

# 样式常量
STYLE_BG = "rgba(30, 30, 30, 250)"
STYLE_TEXT = "#e0e0e0"
STYLE_ACCENT = "#569cd6"
STYLE_SUCCESS = "#4ec9b0"
STYLE_ERROR = "#f48771"
STYLE_TOOL_CALL = "#dcdcaa"


class GenericChatDialog(QDialog):
    """GenericAgent 任务执行聊天窗口"""

    def __init__(self, llm_client, parent=None):
        super().__init__(parent)
        # 使用独立的 LLM 客户端，避免与气泡聊天共享历史
        from systems.ai.llm_client import LLMClient
        from core.config import LLMConfig
        config = LLMConfig()
        # 使用内网 API 配置
        self.llm_client = LLMClient(config)
        self._chat_in_progress = False
        self._response_buffer = ""

        self.setWindowTitle("宠物助手 - 任务执行")
        self.setMinimumSize(900, 650)
        self.setStyleSheet(f"QDialog {{ background-color: {STYLE_BG}; color: {STYLE_TEXT}; }}")

        # 居中显示
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            center = screen.geometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)

        self._setup_ui()
        self._add_welcome()

    def _setup_ui(self):
        """设置UI布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 顶部工具栏
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)

        # 主体区域：聊天 + 输出面板
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 聊天区域
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont("Microsoft YaHei", 10))
        self.chat_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1e1e1e;
                color: {STYLE_TEXT};
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        chat_layout.addWidget(self.chat_area)
        splitter.addWidget(chat_container)

        # 输出面板
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 0, 0, 0)

        output_label = QLabel("输出")
        output_label.setFont(QFont("Microsoft YaHei", 9))
        output_label.setStyleSheet(f"color: {STYLE_ACCENT};")
        output_layout.addWidget(output_label)

        self.output_panel = QTextEdit()
        self.output_panel.setReadOnly(True)
        self.output_panel.setFont(QFont("Consolas", 9))
        self.output_panel.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        output_layout.addWidget(self.output_panel)
        splitter.addWidget(output_container)

        splitter.setSizes([550, 350])
        main_layout.addWidget(splitter)

        # 底部输入区
        input_layout = self._create_input_area()
        main_layout.addLayout(input_layout)

    def _create_toolbar(self):
        """创建工具栏"""
        layout = QHBoxLayout()

        # 标题
        title = QLabel("🤖 宠物助手")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {STYLE_ACCENT};")
        layout.addWidget(title)

        layout.addStretch()

        # 按钮
        self.history_btn = QPushButton("执行历史")
        self.history_btn.setStyleSheet(self._btn_style())
        self.history_btn.clicked.connect(self._show_history)
        layout.addWidget(self.history_btn)

        self.skills_btn = QPushButton("技能树")
        self.skills_btn.setStyleSheet(self._btn_style())
        self.skills_btn.clicked.connect(self._show_skills)
        layout.addWidget(self.skills_btn)

        self.settings_btn = QPushButton("设置")
        self.settings_btn.setStyleSheet(self._btn_style())
        self.settings_btn.clicked.connect(self._show_settings)
        layout.addWidget(self.settings_btn)

        return layout

    def _create_input_area(self):
        """创建输入区域"""
        layout = QHBoxLayout()

        self.input_box = QLineEdit()
        self.input_box.setFont(QFont("Microsoft YaHei", 10))
        self.input_box.setPlaceholderText("输入任务描述...")
        self.input_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2d2d2d;
                color: {STYLE_TEXT};
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border-color: {STYLE_ACCENT};
            }}
            QLineEdit::placeholder {{
                color: #6a6a6a;
            }}
        """)
        self.input_box.returnPressed.connect(self._send_message)
        layout.addWidget(self.input_box)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFont(QFont("Microsoft YaHei", 10))
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: #1177bb;
            }}
            QPushButton:disabled {{
                background-color: #3c3c3c;
                color: #6a6a6a;
            }}
        """)
        self.send_btn.clicked.connect(self._send_message)
        layout.addWidget(self.send_btn)

        return layout

    def _btn_style(self):
        return f"""
            QPushButton {{
                background-color: #3c3c3c;
                color: {STYLE_TEXT};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: #4c4c4c;
            }}
        """

    def _add_welcome(self):
        """添加欢迎消息"""
        welcome = """你好！我是宠物助手，可以帮你完成任务。

**我可以帮你：**
- 编写和运行 Python 代码
- 读写文件和搜索内容
- 扫描网页获取信息
- 执行自动化任务

告诉我你想做什么？"""
        self._add_message("assistant", welcome)

    def _add_message(self, role: str, content: str):
        """添加消息到聊天区"""
        icon = "🤖" if role == "assistant" else "👤"
        color = STYLE_ACCENT if role == "assistant" else STYLE_SUCCESS

        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if cursor.position() > 0:
            cursor.insertText("\n\n")

        cursor.insertHtml(f'<span style="color:{color};font-weight:bold;">{icon}</span> ')
        cursor.insertText(content)

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
        self._add_message("user", text)

        # 调用 Agent 执行
        self._handle_user_input(text)

    def _handle_user_input(self, user_input: str):
        """处理用户输入，调用 Agent 执行"""
        from systems.generic_agent.agent_loop import agent_runner_loop
        from systems.generic_agent.handlers.generic_handler import GenericHandler

        handler = GenericHandler(self)

        system_prompt = """你是宠物的任务执行助手，可以通过调用工具来完成任务。

可用工具:
- code_run: 执行 Python 代码
- file_read: 读取文件
- file_write: 写入文件
- web_scan: 扫描网页

当你需要执行代码时，输出:
```json
{"tool": "code_run", "args": {"code": "你的代码"}}
```

当你需要读取文件时，输出:
```json
{"tool": "file_read", "args": {"path": "文件路径"}}
```

当你需要扫描网页时，输出:
```json
{"tool": "web_scan", "args": {"url": "网址"}}
```

当你完成任务时，说"任务完成"并输出:
```json
{"tool": "exit", "args": {}}
```"""

        # 异步执行
        def run_agent():
            try:
                for step in agent_runner_loop(
                    client=self.llm_client,
                    system_prompt=system_prompt,
                    user_input=user_input,
                    handler=handler,
                    tools_schema=[],
                    verbose=True
                ):
                    # 在主线程更新UI
                    QTimer.singleShot(0, lambda s=step: self._process_step(s))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._handle_error(str(e)))

        import threading
        threading.Thread(target=run_agent, daemon=True).start()

    def _process_step(self, step):
        """处理 Agent 步骤"""
        step_type = step.get("type", "")

        if step_type == "tool_call":
            tool = step.get("tool", "")
            args = step.get("args", {})
            self._add_output(f"🔧 工具: {tool}")
            if args:
                args_str = str(args)[:200] + "..." if len(str(args)) > 200 else str(args)
                self._add_output(f"   参数: {args_str}", color=STYLE_TOOL_CALL)

        elif step_type == "tool_result":
            tool = step.get("tool", "")
            result = step.get("result", {})
            self._add_output(f"✅ 结果 ({tool}):")
            result_str = str(result)[:500]
            if len(str(result)) > 500:
                result_str += "\n... (已截断)"
            self._add_output(f"   {result_str}")

        elif step_type == "text":
            self._add_message("assistant", step.get("content", ""))

        elif step_type == "error":
            self._add_output(f"❌ 错误: {step.get('error', '')}", is_error=True)

        elif step_type == "done":
            self._chat_in_progress = False
            self.send_btn.setEnabled(True)
            self._add_output("\n✅ 执行完成\n", color=STYLE_SUCCESS)

    def _handle_error(self, error: str):
        """处理错误"""
        self._add_output(f"❌ 错误: {error}", is_error=True)
        self._chat_in_progress = False
        self.send_btn.setEnabled(True)

    def _add_output(self, text: str, color: str = None):
        """添加输出到面板"""
        if color is None:
            color = STYLE_TEXT

        cursor = self.output_panel.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(f'<span style="color:{color};font-family:Consolas;font-size:9pt;">{text.replace(chr(10), "<br>")}</span><br>')
        self.output_panel.setTextCursor(cursor)
        self.output_panel.ensureCursorVisible()

    def _show_history(self):
        """显示执行历史"""
        self._add_output("📋 暂未实现执行历史功能")

    def _show_skills(self):
        """显示技能树"""
        try:
            from systems.generic_agent.memory.skill_manager import SkillManager
            manager = SkillManager()
            skills = manager.list_skills()
            if skills:
                self._add_output("🌳 技能树:")
                for skill in skills:
                    self._add_output(f"   - {skill}")
            else:
                self._add_output("🌳 暂无技能，执行任务后会自动学习")
        except Exception as e:
            self._add_output(f"❌ 无法加载技能: {e}")

    def _show_settings(self):
        """显示设置"""
        self._add_output("⚙️ 暂未实现设置功能")