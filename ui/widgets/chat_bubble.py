from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QFontMetrics

# 星露谷明亮调色板
PIXEL_TEXT = "#3f2f25"
PIXEL_BG = "rgba(245, 240, 225, 250)"
PIXEL_BORDER = "#8b6914"


class ChatBubble(QLabel):
    MAX_CHARS_PER_LINE = 25  # 每行最大字符数（增加以支持更长行）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip)

        self._text = ""
        self._displayed_chars = 0
        self._char_speed = 30
        self._timer = QTimer()
        self._timer.timeout.connect(self._type_next_char)
        self._hide_timer = QTimer()
        self._hide_timer.timeout.connect(self.hide)
        self._pending_text = ""
        self._locked_until = 0  # 锁定结束时间（毫秒时间戳）

        font = QFont("Microsoft YaHei UI", 10)
        font.setBold(False)
        self.setFont(font)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self.setStyleSheet(f"""
            QLabel {{
                color: {PIXEL_TEXT};
                background-color: {PIXEL_BG};
                border: 3px solid {PIXEL_BORDER};
                border-radius: 12px;
                padding: 6px 12px;
                font-family: "Microsoft YaHei UI", "PingFang SC", "SimHei", sans-serif;
                font-size: 12px;
            }}
        """)

    def _calc_max_width(self):
        """计算最大宽度"""
        fm = QFontMetrics(self.font())
        return fm.horizontalAdvance("一" * self.MAX_CHARS_PER_LINE) + 30

    def show_text(self, text: str, parent_pos: tuple = None, duration: int = 4000):
        """显示文字气泡
        Args:
            text: 显示的文字
            parent_pos: 父窗口位置
            duration: 显示持续时间（毫秒）
        """
        from PySide6.QtCore import QDateTime
        current_time = QDateTime.currentMSecsSinceEpoch()

        # 如果气泡被锁定且尚未到期，跳过更新
        if self._locked_until > current_time and self.isVisible():
            return

        self._text = text
        self._displayed_chars = len(text)
        self.setText(text)
        self.adjustSize()
        self._hide_timer.stop()
        self._hide_timer.start(duration)
        self.show()

    def resizeEvent(self, event):
        """尺寸变化时确保完整显示"""
        super().resizeEvent(event)

    def minimumSizeHint(self):
        """返回最小尺寸建议"""
        fm = QFontMetrics(self.font())
        max_width = self._calc_max_width()
        # 计算文字需要的尺寸
        metrics = fm.boundingRect(0, 0, max_width, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self._text)
        width = min(metrics.width() + 30, max_width)
        height = metrics.height() + 20  # padding
        return QSize(max(50, width), max(30, height))

    def _type_next_char(self):
        if self._displayed_chars < len(self._text):
            self._displayed_chars += 1
            self.setText(self._text[:self._displayed_chars])
            self.adjustSize()
        else:
            self._timer.stop()

    def hide(self):
        self._timer.stop()
        self._hide_timer.stop()
        super().hide()

    def mousePressEvent(self, event):
        self.hide()


from PySide6.QtCore import QSize
from PySide6.QtWidgets import QSizePolicy