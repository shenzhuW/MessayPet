# ui/settings_dialog.py
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QCheckBox, QPushButton, QListWidget,
    QListWidgetItem, QLineEdit, QGroupBox, QFormLayout, QScrollArea,
    QSlider, QGridLayout
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon

from PIL import Image
import io

PIXEL_ICON_SIZE = 32


def create_pixel_gear_icon(size=32) -> QPixmap:
    """Create a pixel-art gear/settings icon using PIL."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    pixels = img.load()

    center = size // 2
    outer = size // 2 - 2
    inner = size // 4

    border = PIXEL_BORDER
    fill = PIXEL_BORDER_DARK

    border_r, border_g, border_b = int(border[1:3], 16), int(border[3:5], 16), int(border[5:7], 16)
    fill_r, fill_g, fill_b = int(fill[1:3], 16), int(fill[3:5], 16), int(fill[5:7], 16)

    for y in range(size):
        for x in range(size):
            dx, dy = x - center, y - center
            dist = (dx * dx + dy * dy) ** 0.5
            angle = (dx != 0 or dy != 0)

            if inner + 1 <= dist <= outer:
                if dist <= inner + 2:
                    pixels[x, y] = (border_r, border_g, border_b, 255)
                else:
                    pixels[x, y] = (fill_r, fill_g, fill_b, 255)
            elif dist < inner:
                pixels[x, y] = (255, 248, 240, 255)

    for i in range(4):
        angle = i * 3.14159 / 2
        teeth_start = outer - 3
        for t in range(3):
            tx = int(center + (teeth_start + t) * (-1 if i in [1, 2] else 1) * abs(round((angle).real, 2) - (0 if i in [0, 3] else 1)) + center * 0)
            ty = int(center + (teeth_start + t) * (-1 if i in [0, 1] else 1) * abs(round((angle).real, 2) - (0 if i in [1, 2] else 1)) + center * 0)

    for i in range(4):
        angle = i * 3.14159 / 2
        dx = int(4 * -((i + 1) % 4 - 1.5))
        dy = int(4 * -(i - 1.5))
        for t in range(3):
            tx = center + int((outer + t - 1) * (-1 if i in [1, 2] else 1) * abs(round((angle / 3.14159).real, 2) * 2 - 1))
            ty = center + int((outer + t - 1) * (-1 if i in [0, 1] else 1) * (1 if i in [0, 3] else -1))
            if 0 <= tx < size and 0 <= ty < size:
                pixels[tx, ty] = (border_r, border_g, border_b, 255)

    for y in range(size):
        for x in range(size):
            dx, dy = x - center, y - center
            dist = (dx * dx + dy * dy) ** 0.5
            if inner + 1 <= dist <= outer:
                is_teeth = False
                for i in range(4):
                    tx = center + int((outer - 1) * (1 if i in [0, 3] else -1) * ((y - center) / outer if abs(y - center) > abs(x - center) else (x - center) / outer * (1 if i in [0, 3] else -1)))
                    if (i == 0 and y < center - inner) or (i == 1 and x > center + inner) or (i == 2 and y > center + inner) or (i == 3 and x < center - inner):
                        is_teeth = True
                if not is_teeth and dist <= inner + 2:
                    pixels[x, y] = (border_r, border_g, border_b, 255)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return QPixmap.fromImage(QPixmap(buf.read()).toImage())


def create_pixel_icon(size=32, pattern="gear") -> QIcon:
    """Create a pixel-art style icon."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    pixels = img.load()

    border_color = (139, 105, 20)    # #8b6914
    fill_color = (93, 64, 55)         # #5d4037
    bg_color = (245, 240, 225)        # Light cream

    if pattern == "gear":
        c = size // 2
        r = size // 2 - 2
        inner = size // 5

        for y in range(size):
            for x in range(size):
                dx, dy = x - c, y - c
                d = (dx * dx + dy * dy) ** 0.5

                if d <= inner:
                    pixels[x, y] = (*bg_color, 255)
                elif inner < d <= r:
                    pixels[x, y] = (*border_color, 255)

        for i in range(8):
            for t in range(4):
                tx = int(c + (r + t) * (-1 if i in [1, 2, 5, 6] else 1) * (1 if abs(i - 2.5) > 2 else 0))
                ty = int(c + (r + t) * (-1 if i in [3, 4, 7, 0] else 1) * (1 if abs(i - 0.5) <= 2 else 0))
                if 0 <= tx < size and 0 <= ty < size and pixels[tx, ty][3] == 0:
                    pixels[tx, ty] = (*fill_color, 255)

        for y in range(size):
            for x in range(size):
                dx, dy = x - c, y - c
                d = (dx * dx + dy * dy) ** 0.5
                if inner < d <= r and pixels[x, y][3] == 255:
                    pixels[x, y] = (*fill_color, 255)

    elif pattern == "pet":
        # 绘制一个可爱的小猫头像
        cat_color = (93, 64, 55)  # 深棕色
        ear_color = (139, 105, 20)  # 金色
        eye_color = (50, 50, 50)  # 深色

        # 脸
        c = size // 2
        r = size // 2 - 2
        for y in range(size):
            for x in range(size):
                dx, dy = x - c, y - c
                d = (dx * dx + dy * dy) ** 0.5
                if d <= r:
                    pixels[x, y] = (*cat_color, 255)

        # 耳朵
        ear_tip_positions = [(c - 8, c - 6), (c + 8, c - 6)]
        for tx, ty in ear_tip_positions:
            for dy in range(-3, 2):
                for dx in range(-2, 3):
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < size and 0 <= ny < size:
                        pixels[nx, ny] = (*ear_color, 255)

        # 眼睛
        eye_positions = [(c - 5, c - 2), (c + 5, c - 2)]
        for ex, ey in eye_positions:
            if 0 <= ex < size and 0 <= ey < size:
                pixels[ex, ey] = (*eye_color, 255)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    data = buf.read()
    pixmap = QPixmap()
    pixmap.loadFromData(data)
    return QIcon(pixmap)

PIXEL_FONT = "Courier New"
PIXEL_BG = "rgba(245, 240, 225, 250)"
PIXEL_BORDER = "#8b6914"
PIXEL_BORDER_DARK = "#5d4037"
PIXEL_TEXT = "#3f2f25"
PIXEL_SELECTED = "#ffcd75"


def apply_pixel_style(widget):
    widget.setStyleSheet(f"""
        * {{
            background-color: {PIXEL_BG};
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            color: {PIXEL_TEXT};
        }}
        QWidget {{
            background-color: {PIXEL_BG};
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            color: {PIXEL_TEXT};
        }}
        QDialog {{
            background-color: {PIXEL_BG};
        }}
        QTabWidget {{
            background-color: {PIXEL_BG};
            border: 3px solid {PIXEL_BORDER};
        }}
        QTabWidget::pane {{
            background-color: {PIXEL_BG};
            border: 2px solid {PIXEL_BORDER};
        }}
        QTabBar {{
            background-color: #d4c8a8;
        }}
        QTabBar::tab {{
            background-color: #d4c8a8;
            color: {PIXEL_TEXT};
            padding: 8px 20px;
            border: 2px solid {PIXEL_BORDER};
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            border-bottom: none;
        }}
        QTabBar::tab:selected {{
            background-color: {PIXEL_SELECTED};
            border-bottom: 2px solid {PIXEL_BG};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: #e4d8b8;
        }}
        QGroupBox {{
            font-family: "{PIXEL_FONT}";
            font-size: 13px;
            color: {PIXEL_TEXT};
            border: 2px solid {PIXEL_BORDER};
            margin-top: 12px;
            padding-top: 12px;
            background-color: {PIXEL_BG};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
        }}
        QFormLayout {{
            background-color: {PIXEL_BG};
        }}
        QFormLayout::item {{
            background-color: {PIXEL_BG};
        }}
        QLabel {{
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            color: {PIXEL_TEXT};
            background-color: transparent;
        }}
        QComboBox {{
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            color: {PIXEL_TEXT};
            background-color: white;
            border: 2px solid {PIXEL_BORDER};
            padding: 4px 8px;
            min-width: 100px;
        }}
        QComboBox:hover {{
            border-color: {PIXEL_BORDER_DARK};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {PIXEL_BORDER_DARK};
            margin-right: 4px;
        }}
        QComboBox QAbstractItemView {{
            background-color: white;
            border: 2px solid {PIXEL_BORDER};
            selection-background-color: {PIXEL_SELECTED};
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
        }}
        QCheckBox {{
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            color: {PIXEL_TEXT};
            background-color: transparent;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 2px solid {PIXEL_BORDER};
            background-color: white;
        }}
        QCheckBox::indicator:hover {{
            border-color: {PIXEL_BORDER_DARK};
        }}
        QCheckBox::indicator:checked {{
            background-color: {PIXEL_SELECTED};
        }}
        QPushButton {{
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            color: {PIXEL_TEXT};
            background-color: #d4c8a8;
            border: 2px solid {PIXEL_BORDER};
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            background-color: {PIXEL_SELECTED};
        }}
        QPushButton:pressed {{
            background-color: #c4b898;
        }}
        QPushButton:disabled {{
            background-color: #e0d8c8;
            color: #aaa;
        }}
        QListWidget {{
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            color: {PIXEL_TEXT};
            background-color: white;
            border: 2px solid {PIXEL_BORDER};
            outline: none;
        }}
        QListWidget::item {{
            padding: 4px;
        }}
        QListWidget::item:selected {{
            background-color: {PIXEL_SELECTED};
            border: 1px solid {PIXEL_BORDER_DARK};
        }}
        QLineEdit {{
            font-family: "{PIXEL_FONT}";
            font-size: 12px;
            color: {PIXEL_TEXT};
            background-color: white;
            border: 2px solid {PIXEL_BORDER};
            padding: 4px 8px;
        }}
        QLineEdit:focus {{
            border-color: {PIXEL_BORDER_DARK};
        }}
        QVBoxLayout {{
            background-color: {PIXEL_BG};
        }}
        QHBoxLayout {{
            background-color: {PIXEL_BG};
        }}
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        QScrollBar:vertical {{
            background-color: {PIXEL_BG};
            width: 12px;
            border: 1px solid {PIXEL_BORDER};
        }}
        QScrollBar::handle:vertical {{
            background-color: #d4c8a8;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {PIXEL_SELECTED};
        }}
        QSlider::groove:horizontal {{
            border: 1px solid {PIXEL_BORDER};
            height: 8px;
            background-color: white;
            margin: 2px 0;
        }}
        QSlider::handle:horizontal {{
            background-color: {PIXEL_BORDER_DARK};
            border: 1px solid {PIXEL_BORDER};
            width: 18px;
            margin: -5px 0;
        }}
        QSlider::handle:horizontal:hover {{
            background-color: {PIXEL_BORDER};
        }}
        QSlider::sub-page:horizontal {{
            background-color: {PIXEL_SELECTED};
        }}
    """)


class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("设置")
        self.setWindowIcon(create_pixel_icon(32, "gear"))
        # 允许调整大小，设置最小尺寸
        self.setMinimumSize(480, 500)
        self.resize(600, 700)
        apply_pixel_style(self)

        # 在屏幕中心打开
        from PySide6.QtGui import QScreen
        from PySide6.QtWidgets import QApplication
        screen: QScreen = QApplication.primaryScreen()
        if screen:
            center = screen.geometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)

        self._setup_ui()

    def _create_general_tab(self) -> QWidget:
        """创建基础设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 15, 5)

        # 宠物大小设置
        size_group = QGroupBox("宠物大小")
        size_layout = QHBoxLayout()

        self.pet_size_combo = QComboBox()
        self.pet_size_combo.addItems(["32x32", "48x48", "64x64", "80x80", "96x96", "128x128", "160x160", "192x192", "256x256"])
        self.pet_size_combo.currentTextChanged.connect(self._on_pet_size_changed)
        size_layout.addWidget(QLabel("大小:"))
        size_layout.addWidget(self.pet_size_combo)
        size_layout.addStretch()
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # LLM 配置 - 宠物对话
        chat_group = QGroupBox("宠物对话 AI（气泡生成）")
        chat_form = QFormLayout()

        self.chat_base_url = QLineEdit()
        self.chat_base_url.setPlaceholderText("https://api.openai.com/v1")
        chat_form.addRow("API 地址:", self.chat_base_url)

        self.chat_api_key = QLineEdit()
        self.chat_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.chat_api_key.setPlaceholderText("API Key（可选）")
        chat_form.addRow("API Key:", self.chat_api_key)

        self.chat_model = QLineEdit()
        self.chat_model.setPlaceholderText("InstructModel")
        chat_form.addRow("模型:", self.chat_model)

        chat_hint = QLabel("用于生成情绪分析和气泡文字")
        chat_hint.setStyleSheet("color: #888; font-size: 11px;")
        chat_form.addRow("", chat_hint)

        chat_group.setLayout(chat_form)
        layout.addWidget(chat_group)

        # LLM 配置 - 宠物聊天
        llm_group = QGroupBox("宠物聊天 AI（对话）")
        llm_form = QFormLayout()

        self.llm_base_url = QLineEdit()
        self.llm_base_url.setPlaceholderText("https://api.openai.com/v1")
        llm_form.addRow("API 地址:", self.llm_base_url)

        self.llm_api_key = QLineEdit()
        self.llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.llm_api_key.setPlaceholderText("API Key（可选）")
        llm_form.addRow("API Key:", self.llm_api_key)

        self.llm_model = QLineEdit()
        self.llm_model.setPlaceholderText("InstructModelQwen3")
        llm_form.addRow("模型:", self.llm_model)

        llm_hint = QLabel("用于宠物自主对话和行为决策")
        llm_hint.setStyleSheet("color: #888; font-size: 11px;")
        llm_form.addRow("", llm_hint)

        llm_group.setLayout(llm_form)
        layout.addWidget(llm_group)

        # 启动设置
        group = QGroupBox("启动设置")
        form = QFormLayout()

        self.autostart_checkbox = QCheckBox("开机自启动")
        self.autostart_checkbox.setChecked(self.config_manager.get_autostart())

        hint = QLabel("程序将在 Windows 启动时自动运行")
        hint.setStyleSheet("color: #888; font-size: 11px;")

        inner = QVBoxLayout()
        inner.addWidget(self.autostart_checkbox)
        inner.addWidget(hint)
        form.addRow("", inner)

        group.setLayout(form)
        layout.addWidget(group)

        # 间隔设置
        interval_group = QGroupBox("气泡间隔设置")
        interval_form = QFormLayout()

        # 气泡间隔
        bubble_layout = QHBoxLayout()
        self.bubble_min_spin = QSlider(Qt.Orientation.Horizontal)
        self.bubble_min_spin.setRange(30, 300)
        self.bubble_min_spin.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.bubble_min_label = QLabel("60秒")
        self.bubble_min_spin.valueChanged.connect(lambda v: self.bubble_min_label.setText(f"{v}秒"))
        bubble_layout.addWidget(self.bubble_min_spin)
        bubble_layout.addWidget(self.bubble_min_label)
        bubble_hint = QLabel("气泡随机触发的间隔范围（30-300秒）")
        bubble_hint.setStyleSheet("color: #888; font-size: 10px;")

        bubble_layout2 = QHBoxLayout()
        self.bubble_max_spin = QSlider(Qt.Orientation.Horizontal)
        self.bubble_max_spin.setRange(60, 600)
        self.bubble_max_spin.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.bubble_max_label = QLabel("300秒")
        self.bubble_max_spin.valueChanged.connect(lambda v: self.bubble_max_label.setText(f"{v}秒"))
        bubble_layout2.addWidget(self.bubble_max_spin)
        bubble_layout2.addWidget(self.bubble_max_label)

        interval_form.addRow("最小间隔:", bubble_layout)
        interval_form.addRow("最大间隔:", bubble_layout2)
        interval_form.addRow("", bubble_hint)

        # 动作间隔
        action_layout = QHBoxLayout()
        self.action_min_spin = QSlider(Qt.Orientation.Horizontal)
        self.action_min_spin.setRange(60, 300)
        self.action_min_spin.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.action_min_label = QLabel("60秒")
        self.action_min_spin.valueChanged.connect(lambda v: self.action_min_label.setText(f"{v}秒"))
        action_layout.addWidget(self.action_min_spin)
        action_layout.addWidget(self.action_min_label)

        action_layout2 = QHBoxLayout()
        self.action_max_spin = QSlider(Qt.Orientation.Horizontal)
        self.action_max_spin.setRange(120, 600)
        self.action_max_spin.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.action_max_label = QLabel("300秒")
        self.action_max_spin.valueChanged.connect(lambda v: self.action_max_label.setText(f"{v}秒"))
        action_layout2.addWidget(self.action_max_spin)
        action_layout2.addWidget(self.action_max_label)

        action_hint = QLabel("动作决策间隔（idle 等待后再次决策的时间）")
        action_hint.setStyleSheet("color: #888; font-size: 10px;")

        interval_form.addRow("动作最小间隔:", action_layout)
        interval_form.addRow("动作最大间隔:", action_layout2)
        interval_form.addRow("", action_hint)

        interval_group.setLayout(interval_form)
        scroll_layout.addWidget(interval_group)

        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        self._load_pet_size()
        self._load_llm_config()
        self._load_interval_settings()
        return widget

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "基础")
        tabs.addTab(self._create_movement_tab(), "移动")
        tabs.addTab(self._create_shortcuts_tab(), "快捷方式")
        tabs.addTab(self._create_skin_tab(), "皮肤")

        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_and_close)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_pet_size(self):
        """加载宠物大小设置"""
        width, height = self.config_manager.load_pet_size()
        size_text = f"{width}x{height}"
        index = self.pet_size_combo.findText(size_text)
        if index >= 0:
            self.pet_size_combo.blockSignals(True)
            self.pet_size_combo.setCurrentIndex(index)
            self.pet_size_combo.blockSignals(False)

    def _on_pet_size_changed(self, text: str):
        """宠物大小改变"""
        if not text:
            return
        width, height = map(int, text.split("x"))
        # 找到 PetWindow 并更新大小
        parent = self.parent()
        while parent and not hasattr(parent, 'set_pet_size'):
            parent = parent.parent()
        if parent and hasattr(parent, 'set_pet_size'):
            parent.set_pet_size(width, height)

    def _load_llm_config(self):
        """加载 LLM 配置"""
        llm_config = self.config_manager.load_llm_config()
        # 宠物对话配置（气泡生成）
        self.chat_base_url.setText(llm_config.get("bubble_base_url", ""))
        self.chat_api_key.setText(llm_config.get("bubble_api_key", ""))
        self.chat_model.setText(llm_config.get("bubble_model", ""))
        # 宠物聊天配置（对话）
        self.llm_base_url.setText(llm_config.get("base_url", ""))
        self.llm_api_key.setText(llm_config.get("api_key", ""))
        self.llm_model.setText(llm_config.get("model", ""))

    def _save_llm_config(self):
        """保存 LLM 配置"""
        llm_config = {
            "provider": "custom",
            # 宠物对话配置（气泡生成）
            "bubble_base_url": self.chat_base_url.text().strip(),
            "bubble_api_key": self.chat_api_key.text().strip(),
            "bubble_model": self.chat_model.text().strip(),
            # 宠物聊天配置（对话）
            "base_url": self.llm_base_url.text().strip(),
            "api_key": self.llm_api_key.text().strip(),
            "model": self.llm_model.text().strip(),
        }
        self.config_manager.save_llm_config(llm_config)

    def _load_interval_settings(self):
        """加载间隔设置"""
        settings = self.config_manager.load_interval_settings()
        self.bubble_min_spin.setValue(settings.get("bubble_min_interval", 60))
        self.bubble_max_spin.setValue(settings.get("bubble_max_interval", 300))
        self.action_min_spin.setValue(settings.get("action_min_interval", 60))
        self.action_max_spin.setValue(settings.get("action_max_interval", 300))

    def _save_interval_settings(self):
        """保存间隔设置"""
        settings = {
            "bubble_min_interval": self.bubble_min_spin.value(),
            "bubble_max_interval": self.bubble_max_spin.value(),
            "action_min_interval": self.action_min_spin.value(),
            "action_max_interval": self.action_max_spin.value(),
        }
        self.config_manager.save_interval_settings(settings)

    def _create_movement_tab(self) -> QWidget:
        """创建移动设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 动作列表
        group = QGroupBox("动作列表")
        inner = QVBoxLayout()

        self.action_list = QListWidget()
        self.action_list.itemSelectionChanged.connect(self._on_action_selected)
        inner.addWidget(self.action_list)

        # 按钮行
        btn_row = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_action)
        remove_btn = QPushButton("删除")
        remove_btn.clicked.connect(self._remove_action)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        inner.addLayout(btn_row)

        group.setLayout(inner)
        layout.addWidget(group)

        # 速度设置
        speed_group = QGroupBox("移动速度")
        speed_form = QFormLayout()

        self.action_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.action_speed_slider.setRange(1, 10)
        self.action_speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.action_speed_label = QLabel("1.0")
        self.action_speed_slider.valueChanged.connect(self._on_speed_slider_changed)

        speed_row = QHBoxLayout()
        speed_row.addWidget(self.action_speed_slider)
        speed_row.addWidget(self.action_speed_label)
        speed_form.addRow("移动速度:", speed_row)

        self.action_display_edit = QLineEdit()
        self.action_display_edit.setPlaceholderText("例如: 慢速、中速、快速")
        self.action_display_edit.textChanged.connect(self._on_display_name_changed)
        speed_form.addRow("显示名称:", self.action_display_edit)

        speed_group.setLayout(speed_form)
        layout.addWidget(speed_group)

        # 帧率设置
        fps_group = QGroupBox("动画帧率")
        fps_form = QFormLayout()

        self.action_fps_slider = QSlider(Qt.Orientation.Horizontal)
        self.action_fps_slider.setRange(1, 24)
        self.action_fps_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.action_fps_label = QLabel("12 FPS")
        self.action_fps_slider.valueChanged.connect(self._on_fps_slider_changed)

        fps_row = QHBoxLayout()
        fps_row.addWidget(self.action_fps_slider)
        fps_row.addWidget(self.action_fps_label)
        fps_form.addRow("帧率:", fps_row)

        fps_hint = QLabel("数值越高动画播放越快（1=很慢，24=很快）")
        fps_hint.setStyleSheet("color: #888; font-size: 10px;")
        fps_form.addRow("", fps_hint)

        fps_group.setLayout(fps_form)
        layout.addWidget(fps_group)

        hint = QLabel("选择动作后可调整速度和显示名称。点击\"添加\"可在添加时预览动画")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)
        layout.addStretch()

        self._load_action_speeds()
        self._load_action_frame_speeds()
        # 选中新加载的第一个动作以更新滑块
        if self.action_list.count() > 0:
            self.action_list.setCurrentRow(0)
        return widget

    def _load_action_speeds(self):
        """加载动作速度配置"""
        from core.animation.skin_manager import SkinManager

        speeds = self.config_manager.load_action_speeds()

        # 从当前皮肤获取所有动画动作
        current_skin = self.config_manager.get_current_skin()
        skin_path = f"skins/{current_skin}"
        skin_manager = SkinManager()
        if os.path.exists(skin_path):
            skin_manager.scan(skin_path)
        skin_animations = skin_manager.available_animations
        action_descriptions = skin_manager.get_action_descriptions()

        # 根据皮肤动画构建默认动作配置
        default_actions = {}
        for anim_name in skin_animations:
            # 优先使用皮肤配置的动作描述
            desc = action_descriptions.get(anim_name, "")
            display_name = desc if desc else anim_name

            if anim_name in ["idle", "crawl", "walk", "run"]:
                speed_map = {
                    "idle": 0,
                    "crawl": 1.0,
                    "walk": 2.0,
                    "run": 4.0,
                }
                # 默认中文名称（如果皮肤没有配置描述）
                if not desc:
                    display_map = {
                        "idle": "待机",
                        "crawl": "爬行 (慢速)",
                        "walk": "走路 (中速)",
                        "run": "奔跑 (快速)",
                    }
                    display_name = display_map.get(anim_name, anim_name)

                default_actions[anim_name] = {
                    "speed": speed_map.get(anim_name, 1.0),
                    "display": display_name
                }
            else:
                # 其他动作默认速度和显示名称
                if anim_name not in default_actions:
                    default_actions[anim_name] = {"speed": 1.0, "display": display_name}

        # 合并保存的配置
        for key, default in default_actions.items():
            if key not in speeds:
                speeds[key] = default
            else:
                speeds[key].setdefault("display", default["display"])

        self._action_speeds = speeds
        self._refresh_action_list()

    def _load_action_frame_speeds(self):
        """加载动作帧率配置"""
        self._action_frame_speeds = self.config_manager.load_action_frame_speeds()

        # 默认帧率
        default_fps = {"idle": 6, "walk": 12, "run": 16, "crawl": 8}
        for key, fps in default_fps.items():
            if key not in self._action_frame_speeds:
                self._action_frame_speeds[key] = fps

    def _refresh_action_list(self):
        """刷新动作列表"""
        self.action_list.clear()
        for action_id, config in self._action_speeds.items():
            display = config.get("display", action_id)
            speed = config.get("speed", 1.0)
            self.action_list.addItem(f"{display} - 速度: {speed}")

    def _on_action_selected(self):
        """动作列表选择改变"""
        row = self.action_list.currentRow()
        if row < 0:
            return
        action_ids = list(self._action_speeds.keys())
        if row < len(action_ids):
            action_id = action_ids[row]
            config = self._action_speeds[action_id]
            if action_id == "idle":
                # idle 速度固定为 0
                self.action_speed_slider.setValue(0)
                self.action_speed_slider.setDisabled(True)
                self.action_display_edit.setText("待机")
                self.action_display_edit.setDisabled(True)
                self.action_fps_slider.setValue(self._action_frame_speeds.get("idle", 6))
                self.action_fps_slider.setDisabled(False)
            else:
                self.action_speed_slider.setValue(int(config.get("speed", 1.0)))
                self.action_speed_slider.setDisabled(False)
                self.action_display_edit.setText(config.get("display", action_id))
                self.action_display_edit.setDisabled(False)
                self.action_fps_slider.setValue(self._action_frame_speeds.get(action_id, 12))
                self.action_fps_slider.setDisabled(False)

    def _on_speed_slider_changed(self, value):
        """滑块值改变时更新显示和配置（idle 不可修改）"""
        self.action_speed_label.setText(f"{value}.0")
        # 更新当前选中动作的速度配置
        row = self.action_list.currentRow()
        if row >= 0:
            action_ids = list(self._action_speeds.keys())
            if row < len(action_ids):
                action_id = action_ids[row]
                if action_id == "idle":
                    # idle 速度固定为 0，不允许修改
                    self.action_speed_slider.setValue(0)
                    return
                if action_id in self._action_speeds:
                    self._action_speeds[action_id]["speed"] = float(value)

    def _on_display_name_changed(self):
        """显示名称改变时更新配置（idle 不可修改）"""
        row = self.action_list.currentRow()
        if row >= 0:
            action_ids = list(self._action_speeds.keys())
            if row < len(action_ids):
                action_id = action_ids[row]
                if action_id == "idle":
                    # idle 显示名称固定，不允许修改
                    self.action_display_edit.setText("待机")
                    return
                if action_id in self._action_speeds:
                    self._action_speeds[action_id]["display"] = self.action_display_edit.text()

    def _on_fps_slider_changed(self, value):
        """帧率滑块改变时更新配置"""
        self.action_fps_label.setText(f"{value} FPS")
        row = self.action_list.currentRow()
        if row >= 0:
            action_ids = list(self._action_speeds.keys())
            if row < len(action_ids):
                action_id = action_ids[row]
                self._action_frame_speeds[action_id] = value

    def _add_action(self):
        """添加新动作"""
        current_skin = self._selected_skin or self.config_manager.get_current_skin()
        dialog = ActionEditDialog(self, skin_name=current_skin)
        if dialog.exec():
            action_id, display, speed = dialog.get_values()
            self._action_speeds[action_id] = {"speed": speed, "display": display}
            self._refresh_action_list()

    def _remove_action(self):
        """删除动作"""
        row = self.action_list.currentRow()
        if row < 0:
            return
        action_ids = list(self._action_speeds.keys())
        if row < len(action_ids):
            action_id = action_ids[row]
            # 不允许删除默认动作
            if action_id in ["crawl", "walk", "run"]:
                return
            del self._action_speeds[action_id]
            self._refresh_action_list()

    def _create_shortcuts_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("网页快捷方式")
        inner = QVBoxLayout()

        self.shortcuts_list = QListWidget()
        inner.addWidget(self.shortcuts_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_shortcut)
        remove_btn = QPushButton("删除")
        remove_btn.clicked.connect(self._remove_shortcut)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        inner.addLayout(btn_row)

        group.setLayout(inner)
        layout.addWidget(group)

        self._load_web_shortcuts()
        return widget

    def _create_skin_tab(self) -> QWidget:
        from core.animation.skin_manager import SkinManager

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 水平布局：左侧皮肤列表 + 右侧详情
        main_layout = QHBoxLayout()

        # 左侧：皮肤列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QLabel("皮肤列表:")
        left_layout.addWidget(list_label)

        self.skin_list_widget = QListWidget()
        self.skin_list_widget.currentRowChanged.connect(self._on_skin_selected)
        left_layout.addWidget(self.skin_list_widget)

        left_hint = QLabel("在 skins/ 目录创建文件夹\n添加动作子文件夹和 config.json 即可")
        left_hint.setStyleSheet("color: #888; font-size: 11px;")
        left_layout.addWidget(left_hint)

        main_layout.addWidget(left_panel, 1)

        # 右侧：皮肤详情
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 皮肤名称
        self.skin_name_label = QLabel("名称: -")
        self.skin_name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.skin_name_label)

        self.skin_status_label = QLabel("")
        right_layout.addWidget(self.skin_status_label)

        # 配置的动作（从 config.json 读取）
        self.configured_group = QGroupBox("配置的动作")
        self.configured_layout = QVBoxLayout()
        self.configured_labels = {}
        self.configured_group.setLayout(self.configured_layout)
        right_layout.addWidget(self.configured_group)

        # 缺失的动作提示
        self.missing_label = QLabel("")
        self.missing_label.setStyleSheet("color: #c44040;")
        right_layout.addWidget(self.missing_label)

        # 可选动作
        optional_group = QGroupBox("可选动作")
        optional_layout = QVBoxLayout()
        self.optional_label = QLabel("-")
        self.optional_label.setWordWrap(True)
        optional_layout.addWidget(self.optional_label)
        optional_group.setLayout(optional_layout)
        right_layout.addWidget(optional_group)

        # 预览区域
        preview_group = QGroupBox("动作预览")
        preview_inner = QHBoxLayout()

        self.skin_preview_combo = QComboBox()
        self.skin_preview_combo.currentTextChanged.connect(self._on_preview_animation_changed)
        preview_inner.addWidget(QLabel("动作:"))
        preview_inner.addWidget(self.skin_preview_combo)

        preview_group.setLayout(preview_inner)
        right_layout.addWidget(preview_group)

        self.skin_preview_label = QLabel("选择皮肤后预览")
        self.skin_preview_label.setFixedSize(120, 120)
        self.skin_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.skin_preview_label.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {PIXEL_BORDER};
                background-color: white;
            }}
        """)
        right_layout.addWidget(self.skin_preview_label)

        right_layout.addStretch()

        main_layout.addWidget(right_panel, 2)
        layout.addLayout(main_layout)

        # 保存当前选择的皮肤名称
        self._selected_skin = None
        self._preview_timer = None
        self._preview_frames = []
        self._preview_index = 0

        # 加载皮肤列表
        self._load_skin_list()

        return widget

    def _load_skin_list(self):
        """加载皮肤列表"""
        from core.animation.skin_manager import SkinManager

        self.skin_list_widget.clear()
        skins = SkinManager.get_available_skins()
        current_skin = self.config_manager.get_current_skin()

        for skin in skins:
            is_current = skin == current_skin
            is_protected = skin == "default"
            display_name = skin
            if is_current:
                display_name += " [使用中]"
            if is_protected:
                display_name += " (内置)"
            self.skin_list_widget.addItem(display_name)

        # 选中当前皮肤
        if current_skin in skins:
            self.skin_list_widget.setCurrentRow(skins.index(current_skin))

    def _on_skin_selected(self, row: int):
        """皮肤选择改变"""
        if row < 0:
            return

        from core.animation.skin_manager import SkinManager

        skins = SkinManager.get_available_skins()
        if row >= len(skins):
            return

        skin_name = skins[row]
        self._selected_skin = skin_name

        # 更新皮肤信息
        self.skin_name_label.setText(f"名称: {skin_name}")

        info = SkinManager.validate_skin(skin_name)

        # 更新配置的动作状态
        for label in self.configured_labels.values():
            label.setParent(None)
        self.configured_labels = {}

        if "error" in info:
            self.skin_status_label.setText(f"✗ {info['error']}")
            self.skin_status_label.setStyleSheet("color: #c44040; font-weight: bold;")
            self.missing_label.setText("")
        else:
            # 显示配置的动作及其状态
            present = set(info["present_required"])
            missing = set(info["missing_required"])

            for anim in present | missing:
                label = QLabel(f"✓ {anim}" if anim in present else f"○ {anim}")
                label.setStyleSheet("color: green; font-weight: bold;" if anim in present else "color: #c44040;")
                self.configured_layout.addWidget(label)
                self.configured_labels[anim] = label

            # 更新缺失提示
            if missing:
                self.missing_label.setText(f"缺失动作: {', '.join(missing)}")
            else:
                self.missing_label.setText("")

            # 更新状态提示
            if info["valid"]:
                self.skin_status_label.setText("✓ 验证通过")
                self.skin_status_label.setStyleSheet("color: green;")
            else:
                self.skin_status_label.setText("✗ 配置的动作缺失")
                self.skin_status_label.setStyleSheet("color: #c44040; font-weight: bold;")

        # 更新预览动作下拉框
        self.skin_preview_combo.blockSignals(True)
        self.skin_preview_combo.clear()
        all_anims = info["present_required"] + info["optional"]
        self.skin_preview_combo.addItems(all_anims)
        self.skin_preview_combo.blockSignals(False)

        # 加载预览
        if all_anims:
            self._load_preview_frames(skin_name, all_anims[0])

    def _load_preview_frames(self, skin_name: str, animation_name: str):
        """加载预览动画帧"""
        from core.animation.skin_manager import SkinManager
        from core.animation.manager import AnimationManager
        from PIL import Image

        # 停止之前的预览
        if self._preview_timer:
            self._preview_timer.stop()
            self._preview_timer = None

        preview_path = SkinManager.get_skin_preview_path(skin_name, animation_name)
        if not preview_path:
            self.skin_preview_label.setText("无预览")
            return

        # 加载帧
        self._preview_frames = []
        anim_dir = os.path.dirname(preview_path)
        frame_files = sorted([
            f for f in os.listdir(anim_dir)
            if f.endswith('.png') or f.endswith('.gif')
        ])

        anim_mgr = AnimationManager()
        for frame_file in frame_files:
            img_path = os.path.join(anim_dir, frame_file)
            img = Image.open(img_path)
            try:
                img = img.convert("RGBA")
                self._preview_frames.append(anim_mgr._pil_to_pixmap(img))
            finally:
                img.close()

        if not self._preview_frames:
            self.skin_preview_label.setText("加载失败")
            return

        # 开始播放预览
        self._preview_index = 0
        self._play_preview_frame()

    def _play_preview_frame(self):
        """播放预览帧"""
        if not self._preview_frames:
            return

        pixmap = self._preview_frames[self._preview_index]
        scaled = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.skin_preview_label.setPixmap(scaled)

        self._preview_index = (self._preview_index + 1) % len(self._preview_frames)

        # 设置定时器
        if self._preview_timer:
            self._preview_timer.stop()
        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._play_preview_frame)
        self._preview_timer.start(150)

    def _on_preview_animation_changed(self, animation_name: str):
        """预览动画选择改变"""
        if not self._selected_skin or not animation_name:
            return
        self._load_preview_frames(self._selected_skin, animation_name)

    def _load_web_shortcuts(self):
        shortcuts = self.config_manager.load_web_shortcuts()
        self.shortcuts_list.clear()
        for s in shortcuts:
            name = s.get("name", "未命名")
            url = s.get("url", "")
            self.shortcuts_list.addItem(f"{name} - {url}")

    def _add_shortcut(self):
        dialog = ShortcutEditDialog(self)
        if dialog.exec():
            name, url = dialog.get_values()
            shortcuts = self.config_manager.load_web_shortcuts()
            shortcuts.append({"name": name, "url": url})
            self.config_manager.save_web_shortcuts(shortcuts)
            self._load_web_shortcuts()

    def _remove_shortcut(self):
        row = self.shortcuts_list.currentRow()
        if row >= 0:
            self.shortcuts_list.takeItem(row)
            shortcuts = self.config_manager.load_web_shortcuts()
            shortcuts.pop(row)
            self.config_manager.save_web_shortcuts(shortcuts)

    def _save_and_close(self):
        # 保存自启动设置
        self.config_manager.set_autostart(self.autostart_checkbox.isChecked())

        # 保存 LLM 配置
        self._save_llm_config()

        # 保存间隔设置
        self._save_interval_settings()

        # 保存动作速度配置
        print(f"[SettingsDialog] 保存前的 _action_speeds: {self._action_speeds}")
        self.config_manager.save_action_speeds(self._action_speeds)

        # 保存帧率配置
        print(f"[SettingsDialog] 保存前的 _action_frame_speeds: {self._action_frame_speeds}")
        self.config_manager.save_action_frame_speeds(self._action_frame_speeds)

        # 实时更新 RandomWalker 速度
        parent = self.parent()
        while parent and not hasattr(parent, '_random_walker'):
            parent = parent.parent()
        if parent and hasattr(parent, '_random_walker') and parent._random_walker:
            print(f"[SettingsDialog] 实时更新 RandomWalker: {self._action_speeds}")
            parent._random_walker.set_action_speeds(self._action_speeds)
        else:
            print(f"[SettingsDialog] 未找到 RandomWalker parent")

        # 实时更新 AnimationManager 帧率
        if parent and hasattr(parent, 'animation_manager') and parent.animation_manager:
            parent.animation_manager.set_action_frame_speeds(self._action_frame_speeds)
            parent.animation_manager.restart_idle_animation()

        # 实时更新间隔设置
        if parent:
            interval_settings = {
                "bubble_min_interval": self.bubble_min_spin.value(),
                "bubble_max_interval": self.bubble_max_spin.value(),
                "action_min_interval": self.action_min_spin.value(),
                "action_max_interval": self.action_max_spin.value(),
            }
            if hasattr(parent, 'update_interval_settings'):
                parent.update_interval_settings(interval_settings)

        # 保存皮肤选择
        if self._selected_skin:
            from core.animation.skin_manager import SkinManager
            validation = SkinManager.validate_skin(self._selected_skin)
            if validation["valid"]:
                self.config_manager.set_current_skin(self._selected_skin)
                # 通知 PetWindow 切换皮肤
                parent = self.parent()
                while parent and not hasattr(parent, 'switch_skin'):
                    parent = parent.parent()
                if parent and hasattr(parent, 'switch_skin'):
                    parent.switch_skin(self._selected_skin)

        self.accept()


class ShortcutEditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加快捷方式")
        self.setFixedSize(320, 120)
        apply_pixel_style(self)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: GitHub")
        form.addRow("名称:", self.name_input)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://github.com")
        form.addRow("网址:", self.url_input)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def get_values(self):
        return self.name_input.text(), self.url_input.text()


class ActionEditDialog(QDialog):
    def __init__(self, parent=None, skin_name="default"):
        super().__init__(parent)
        self.setWindowTitle("添加动作")
        self.setFixedSize(400, 320)
        self._skin_name = skin_name
        apply_pixel_style(self)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("例如: sneak, trot, sprint")
        form.addRow("动作ID:", self.id_input)

        self.display_input = QLineEdit()
        self.display_input.setPlaceholderText("例如: 潜行、小跑、冲刺")
        form.addRow("显示名称:", self.display_input)

        self.speed_input = QSlider(Qt.Orientation.Horizontal)
        self.speed_input.setRange(1, 10)
        self.speed_input.setValue(2)
        speed_label = QLabel("2.0")
        self.speed_input.valueChanged.connect(lambda v: (
            speed_label.setText(f"{v}.0"),
            self._restart_preview_if_playing()
        ))
        speed_row = QHBoxLayout()
        speed_row.addWidget(self.speed_input)
        speed_row.addWidget(speed_label)
        form.addRow("速度:", speed_row)

        layout.addLayout(form)

        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout()

        # 预览标签和按钮在同一行
        preview_top = QHBoxLayout()
        self.preview_label = QLabel("选择动作后\n点击预览")
        self.preview_label.setFixedSize(160, 120)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {PIXEL_BORDER};
                background-color: white;
            }}
        """)
        preview_top.addWidget(self.preview_label)

        preview_btn_col = QVBoxLayout()
        preview_btn = QPushButton("预览动画")
        preview_btn.clicked.connect(self._preview_animation)
        preview_btn_col.addWidget(preview_btn)
        preview_btn_col.addStretch()

        hint = QLabel(f"播放 skins/{self._skin_name}/\n动作ID/ 下的帧")
        hint.setStyleSheet("color: #888; font-size: 10px;")
        preview_btn_col.addWidget(hint)
        preview_top.addLayout(preview_btn_col)

        preview_layout.addLayout(preview_top)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self._preview_timer = None
        self._preview_frames = []
        self._preview_index = 0
        self._is_preview_playing = False

    def _preview_animation(self):
        """预览动画"""
        action_id = self.id_input.text().strip()
        if not action_id:
            self.preview_label.setText("请输入动作ID")
            return

        import os
        from PySide6.QtGui import QPixmap, QImage
        from PIL import Image
        from core.animation.manager import AnimationManager

        # 查找动画帧（使用当前皮肤）
        anim_dir = f"skins/{self._skin_name}/{action_id}"
        if not os.path.exists(anim_dir):
            self.preview_label.setText(f"未找到\n{anim_dir}")
            return

        frame_files = sorted([
            f for f in os.listdir(anim_dir)
            if f.endswith('.png') or f.endswith('.gif')
        ])

        if not frame_files:
            self.preview_label.setText("没有找到帧文件")
            return

        # 加载帧
        self._preview_frames = []
        anim_mgr = AnimationManager()
        for frame_file in frame_files:
            img_path = os.path.join(anim_dir, frame_file)
            img = Image.open(img_path)
            try:
                img = img.convert("RGBA")
                self._preview_frames.append(anim_mgr._pil_to_pixmap(img))
            finally:
                img.close()

        if not self._preview_frames:
            self.preview_label.setText("加载失败")
            return

        # 开始播放
        self._preview_index = 0
        self._is_preview_playing = True
        self._play_preview_frame()

    def _restart_preview_if_playing(self):
        """如果正在预览，重新开始播放"""
        if self._is_preview_playing and self._preview_frames:
            if self._preview_timer:
                self._preview_timer.stop()
            self._preview_index = 0
            self._play_preview_frame()

    def _play_preview_frame(self):
        """播放预览帧"""
        if not self._preview_frames:
            return

        pixmap = self._preview_frames[self._preview_index]
        scaled = pixmap.scaled(160, 120)
        self.preview_label.setPixmap(scaled)

        self._preview_index = (self._preview_index + 1) % len(self._preview_frames)

        # 停止之前的定时器
        if self._preview_timer:
            self._preview_timer.stop()

        # 根据速度计算间隔：速度越高，播放越快
        # 基础间隔 300ms（速度1），每增加1速度减少25ms，最低50ms
        speed = self.speed_input.value()
        interval = max(50, 300 - (speed - 1) * 25)

        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._play_preview_frame)
        self._preview_timer.start(interval)

    def get_values(self):
        # 停止预览
        if self._preview_timer:
            self._preview_timer.stop()
            self._preview_timer = None
        self._is_preview_playing = False

        return (
            self.id_input.text(),
            self.display_input.text(),
            float(self.speed_input.value())
        )