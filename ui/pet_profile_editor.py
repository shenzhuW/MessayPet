# ui/pet_profile_editor.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QPushButton, QDialogButtonBox, QLabel, QComboBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from systems.ai.memory_manager import MemoryManager
import time

PIXEL_BG = "rgba(245, 240, 225, 250)"
PIXEL_BORDER = "#8b6914"

class PetProfileEditor(QDialog):
    def __init__(self, memory_manager: MemoryManager, stat_manager=None, parent=None):
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.stat_manager = stat_manager
        self.pet_profile = memory_manager.get_pet_profile()

        self.setWindowTitle("编辑角色卡")
        self.setFixedSize(500, 600)
        self.setStyleSheet(f"QDialog {{ background-color: {PIXEL_BG}; }}")

        # 设置窗口图标
        from ui.settings_dialog import create_pixel_icon
        self.setWindowIcon(create_pixel_icon(32, "pet"))

        self._setup_ui()
        self._load_profile()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(10)

        self.name_edit = QLineEdit()
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["未知", "公", "母"])
        self.species_edit = QLineEdit()
        self.personality_edit = QLineEdit()
        self.age_label = QLabel()  # 只读显示年龄
        self.age_label.setStyleSheet("color: #666; font-style: italic;")
        self.appearance_edit = QTextEdit()
        self.background_edit = QTextEdit()
        self.speech_style_edit = QLineEdit()
        self.abilities_edit = QLineEdit()
        self.likes_edit = QLineEdit()
        self.dislikes_edit = QLineEdit()

        form.addRow("名字:", self.name_edit)
        form.addRow("性别:", self.gender_combo)
        form.addRow("种类:", self.species_edit)
        form.addRow("性格:", self.personality_edit)
        form.addRow("年龄:", self.age_label)
        form.addRow("外观:", self.appearance_edit)
        form.addRow("背景:", self.background_edit)
        form.addRow("说话风格:", self.speech_style_edit)
        form.addRow("能力:", self.abilities_edit)
        form.addRow("喜欢:", self.likes_edit)
        form.addRow("不喜欢:", self.dislikes_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_profile(self):
        data = self.pet_profile.get_all()
        self.name_edit.setText(data.get("name", ""))

        # 性别
        gender = data.get("gender", "未知")
        self.gender_combo.setCurrentText(gender)

        self.species_edit.setText(data.get("species", ""))
        self.personality_edit.setText(data.get("personality", ""))

        # 年龄计算（基于 stat_manager 的出生时间）
        age_text = self._calculate_age()
        self.age_label.setText(age_text if age_text else "未知")

        self.appearance_edit.setPlainText(data.get("appearance", ""))
        self.background_edit.setPlainText(data.get("background", ""))
        self.speech_style_edit.setText(data.get("speech_style", ""))
        self.abilities_edit.setText(", ".join(data.get("abilities", [])))
        self.likes_edit.setText(", ".join(data.get("likes", [])))
        self.dislikes_edit.setText(", ".join(data.get("dislikes", [])))

    def _calculate_age(self) -> str:
        """计算宠物年龄"""
        print(f"[PetProfileEditor] stat_manager: {self.stat_manager}")
        if self.stat_manager:
            print(f"[PetProfileEditor] has get_birth_date: {hasattr(self.stat_manager, 'get_birth_date')}")
            birth_date = self.stat_manager.get_birth_date() if hasattr(self.stat_manager, 'get_birth_date') else None
            age_days = self.stat_manager.get_age_days() if hasattr(self.stat_manager, 'get_age_days') else 0
            print(f"[PetProfileEditor] birth_date: {birth_date}, age_days: {age_days}")
            if birth_date and age_days > 0:
                years = int(age_days // 365)
                days = int(age_days % 365)
                if years > 0:
                    return f"{years}岁{days}天"
                else:
                    return f"{days}天"
        return ""

    def _save(self):
        self.pet_profile.set("name", self.name_edit.text())
        self.pet_profile.set("gender", self.gender_combo.currentText())
        self.pet_profile.set("species", self.species_edit.text())
        self.pet_profile.set("personality", self.personality_edit.text())
        self.pet_profile.set("appearance", self.appearance_edit.toPlainText())
        self.pet_profile.set("background", self.background_edit.toPlainText())
        self.pet_profile.set("speech_style", self.speech_style_edit.text())

        abilities = [a.strip() for a in self.abilities_edit.text().split(",") if a.strip()]
        self.pet_profile.set("abilities", abilities)

        likes = [l.strip() for l in self.likes_edit.text().split(",") if l.strip()]
        self.pet_profile.set("likes", likes)

        dislikes = [d.strip() for d in self.dislikes_edit.text().split(",") if d.strip()]
        self.pet_profile.set("dislikes", dislikes)

        self.accept()