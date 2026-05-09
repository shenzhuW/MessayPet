# ui/pet_assistant_window.py
"""
宠物助手窗口入口
通过右键菜单触发
"""
import threading
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

from pet_assistant.ui.main_window import ChatPanel


class PetAssistantWindow(QWidget):
    """宠物助手窗口"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        super().__init__()
        self.setWindowTitle("🌟 宠物助手")
        self.setMinimumSize(400, 500)
        self.resize(480, 650)

        # 创建 Agent
        from pet_assistant.engine import GeneraticAgent
        self.agent = GeneraticAgent()
        threading.Thread(target=self.agent.run, daemon=True, name="PetAgent").start()

        # 创建 ChatPanel
        self.chat_panel = ChatPanel(self.agent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chat_panel)

    def closeEvent(self, event):
        self.hide()
        event.ignore()