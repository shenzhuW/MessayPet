from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy
from PySide6.QtCore import QTimer, Qt, QPoint, QRect, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QColor, QBrush, QPen, QPainterPath, QPolygon, QRegion

# 星露谷调色板
PIXEL_TEXT = "#3f2f25"
PIXEL_BG = "#F5F0E1"
PIXEL_BORDER = "#8b6914"
BORDER_WAITING = "#c44040"
BORDER_COMPLETE = "#5a9c32"


class ChatBubble(QWidget):
    """高级气泡组件 - 使用 QWidget + QPainter 实现"""

    MAX_CHARS_PER_LINE = 25

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._text = ""
        self._displayed_chars = 0
        self._char_speed = 30
        self._timer = QTimer()
        self._timer.timeout.connect(self._type_next_char)
        self._hide_timer = QTimer()
        self._hide_timer.timeout.connect(self._on_hide_timeout)
        self._current_hide_duration = 0
        self._pending_text = ""
        self._locked_until = 0
        self._border_color = QColor(PIXEL_BORDER)
        self._bg_color = QColor(PIXEL_BG)
        self._text_color = QColor(PIXEL_TEXT)  # 默认文字颜色

        # 气泡尾巴位置（相对于右下角）
        self._tail_direction = "left"  # left, right, bottom
        self._tail_offset = 15  # 尾巴在边缘的偏移

        # 阴影
        self._shadow_enabled = True
        self._shadow_offset = 3
        self._shadow_blur = 8
        self._shadow_color = QColor(0, 0, 0, 60)

        # 动画
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._scale_anim = None
        self._opacity = 1.0
        self._is_hiding = False  # 防止动画期间重复触发

        # 字体
        self._font = QFont("Microsoft YaHei UI", 10)
        self._font.setBold(False)

        # 隐藏气泡时重置
        self._pending_hide = False

    def _calc_max_width(self):
        """计算最大宽度"""
        fm = QFontMetrics(self._font)
        return fm.horizontalAdvance("一" * self.MAX_CHARS_PER_LINE) + 40

    def show_text(self, text: str, parent_pos: tuple = None, duration: int = 4000):
        """显示文字气泡"""
        from PySide6.QtCore import QDateTime
        current_time = QDateTime.currentMSecsSinceEpoch()

        if self._locked_until > current_time and self.isVisible():
            return

        # 停止所有动画和定时器
        self._fade_anim.stop()
        self._hide_timer.stop()
        self._timer.stop()
        self._is_hiding = False

        self._text = text
        self._displayed_chars = len(text)

        # 预先计算尺寸
        self._calculate_and_resize()

        # 确保窗口可见且不透明
        self.show()
        self.raise_()
        self.setWindowOpacity(1.0)

        # 启动隐藏定时器
        self._current_hide_duration = duration
        self._hide_timer.start(duration)

    def _show_with_animation(self):
        """带动画显示"""
        self.show()
        self._opacity = 0.0
        self.setWindowOpacity(0.0)

        # 淡入动画
        self._fade_anim.stop()
        self._fade_anim.setDuration(200)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

        self._timer.start(self._char_speed)

    def _type_next_char(self):
        if self._displayed_chars < len(self._text):
            self._displayed_chars += 1
            self.update()
        else:
            self._timer.stop()

    def hide(self):
        if self._is_hiding:
            return
        self._is_hiding = True

        self._timer.stop()
        self._hide_timer.stop()
        self._locked_until = 0

        # 快速淡出然后隐藏
        self._fade_anim.stop()
        self._fade_anim.setDuration(100)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._do_hide)
        self._fade_anim.start()

    def _do_hide(self):
        """执行真正的隐藏"""
        self._is_hiding = False
        self.setWindowOpacity(1.0)
        super().hide()

    def _on_hide_timeout(self):
        """隐藏定时器触发"""
        self.hide()

    def set_border_color(self, color: str):
        """设置边框颜色"""
        self._border_color = QColor(color)
        self._text_color = QColor(color)  # 同步修改文字颜色
        self.update()

    def set_text_color(self, color: str):
        """单独设置文字颜色"""
        self._text_color = QColor(color)
        self.update()

    def set_waiting(self):
        """等待确认状态"""
        self.set_border_color(BORDER_WAITING)

    def set_complete(self):
        """已完成状态"""
        self.set_border_color(BORDER_COMPLETE)

    def reset_border(self):
        """恢复默认边框"""
        self.set_border_color(PIXEL_BORDER)

    def set_tail_direction(self, direction: str):
        """设置气泡尾巴方向: left, right, bottom"""
        self._tail_direction = direction
        self.update()

    def _calculate_and_resize(self):
        """预先计算气泡尺寸"""
        padding = 12
        fm = QFontMetrics(self._font)
        max_width = self._calc_max_width() - 40

        display_text = self._text[:self._displayed_chars]
        text_rect = fm.boundingRect(
            0, 0, max_width, 0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            display_text
        )

        bubble_width = max(80, min(text_rect.width() + padding * 2, max_width))
        bubble_height = text_rect.height() + padding * 2
        tail_size = 12

        if self._tail_direction == "bottom":
            bubble_height += tail_size

        self.resize(bubble_width, bubble_height)

    def paintEvent(self, event):
        """自定义绘制气泡"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # 气泡尺寸（使用已计算的尺寸）
        bubble_width = self.width()
        bubble_height = self.height()
        padding = 12
        tail_size = 12

        # 绘制文字
        display_text = self._text[:self._displayed_chars]

        # 气泡矩形区域
        bubble_rect = QRect(0, 0, bubble_width, bubble_height)
        if self._tail_direction == "bottom":
            bubble_rect = QRect(0, 0, bubble_width, bubble_height - tail_size)

        # 使用圆角矩形区域设置 Mask，使圆角外透明
        radius = 12
        region = QRegion(bubble_rect)
        # 减去四个圆角
        tl = QRegion(bubble_rect.left(), bubble_rect.top(), radius, radius, QRegion.RegionType.Rectangle)
        tr = QRegion(bubble_rect.right() - radius + 1, bubble_rect.top(), radius, radius, QRegion.RegionType.Rectangle)
        bl = QRegion(bubble_rect.left(), bubble_rect.bottom() - radius + 1, radius, radius, QRegion.RegionType.Rectangle)
        br = QRegion(bubble_rect.right() - radius + 1, bubble_rect.bottom() - radius + 1, radius, radius, QRegion.RegionType.Rectangle)
        rounded = region.subtracted(tl).subtracted(tr).subtracted(bl).subtracted(br)
        # 添加四个圆角
        corners = [
            QRegion(bubble_rect.left(), bubble_rect.top(), radius, radius, QRegion.RegionType.Ellipse),
            QRegion(bubble_rect.right() - radius + 1, bubble_rect.top(), radius, radius, QRegion.RegionType.Ellipse),
            QRegion(bubble_rect.left(), bubble_rect.bottom() - radius + 1, radius, radius, QRegion.RegionType.Ellipse),
            QRegion(bubble_rect.right() - radius + 1, bubble_rect.bottom() - radius + 1, radius, radius, QRegion.RegionType.Ellipse),
        ]
        self.setMask(rounded.united(corners[0]).united(corners[1]).united(corners[2]).united(corners[3]))

        # 设置裁剪路径
        clip_path = QPainterPath()
        clip_path.addRoundedRect(bubble_rect, radius, radius)
        painter.setClipPath(clip_path)

        # 绘制阴影
        if self._shadow_enabled:
            painter.save()
            shadow_rect = bubble_rect.adjusted(
                self._shadow_offset, self._shadow_offset,
                self._shadow_offset, self._shadow_offset
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
            self._draw_rounded_rect(painter, shadow_rect, 12)
            painter.restore()

        # 绘制背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        self._draw_rounded_rect(painter, bubble_rect, 12)

        # 绘制边框
        pen = QPen(self._border_color, 3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        self._draw_rounded_rect(painter, bubble_rect, 12)

        # 绘制气泡尾巴
        self._draw_tail(painter, bubble_rect)

        # 绘制文字
        painter.setFont(self._font)
        painter.setPen(QPen(self._text_color))
        painter.drawText(
            bubble_rect.adjusted(padding, padding, -padding, -padding),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            display_text
        )

    def _draw_rounded_rect(self, painter: QPainter, rect: QRect, radius: int):
        """绘制圆角矩形"""
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.drawPath(path)

    def _draw_tail(self, painter: QPainter, bubble_rect: QRect):
        """绘制气泡尾巴"""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._bg_color))

        tail_path = QPainterPath()
        x = bubble_rect.width() - self._tail_offset - 10
        y = bubble_rect.height() - 5

        if self._tail_direction == "left":
            # 左下角尾巴（指向上方）
            tail_path.moveTo(x, y + 15)
            tail_path.lineTo(x - 8, y + 15)
            tail_path.lineTo(x - 5, y + 5)
            tail_path.lineTo(x - 2, y + 15)
            tail_path.closeSubpath()
        elif self._tail_direction == "right":
            # 右下角尾巴
            tail_path.moveTo(x, y + 15)
            tail_path.lineTo(x + 8, y + 15)
            tail_path.lineTo(x + 5, y + 5)
            tail_path.lineTo(x + 2, y + 15)
            tail_path.closeSubpath()
        elif self._tail_direction == "bottom":
            # 底部中央尾巴
            cx = bubble_rect.width() // 2
            tail_path.moveTo(cx - 8, bubble_rect.height())
            tail_path.lineTo(cx + 8, bubble_rect.height())
            tail_path.lineTo(cx, bubble_rect.height() + 12)
            tail_path.closeSubpath()

        painter.drawPath(tail_path)

        # 重新绘制边框尾巴部分
        pen = QPen(self._border_color, 3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(tail_path)

    def mousePressEvent(self, event):
        self.hide()
        self.reset_border()

    def minimumSizeHint(self):
        return QSize(80, 40)