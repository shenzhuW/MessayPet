# ui/tray_manager.py
"""系统托盘管理器 - 为桌面宠物添加托盘图标"""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QIcon, QPixmap, QAction, QPainter


class TrayManager(QObject):
    """系统托盘管理器"""

    # 信号
    quit_requested = Signal()  # 退出程序请求
    show_requested = Signal()  # 显示宠物请求
    hide_requested = Signal()  # 隐藏宠物请求

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray_icon = None
        self._menu = None
        self._is_visible = False
        self._pet_window = None

    def setup(self, icon_path: str = None, pet_window=None):
        """初始化托盘图标"""
        self._pet_window = pet_window

        # 创建托盘图标
        self._tray_icon = QSystemTrayIcon()

        # 设置图标
        if icon_path:
            self._tray_icon.setIcon(QIcon(icon_path))
        else:
            # 使用默认图标
            self._tray_icon.setIcon(self._create_default_icon())

        # 创建右键菜单
        self._menu = QMenu()

        # 显示/隐藏宠物
        self._show_action = QAction("显示宠物", self._menu)
        self._show_action.triggered.connect(self._toggle_pet_visibility)
        self._menu.addAction(self._show_action)

        self._menu.addSeparator()

        # 退出选项
        self._quit_action = QAction("退出", self._menu)
        self._quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(self._quit_action)

        self._tray_icon.setContextMenu(self._menu)

        # 双击显示/隐藏宠物
        self._tray_icon.activated.connect(self._on_tray_activated)

        # 显示托盘图标
        self._tray_icon.show()
        self._is_visible = True

        # 设置提示文本
        self._tray_icon.setToolTip("桌面宠物")

    def _create_default_icon(self) -> QIcon:
        """创建默认图标"""
        # 尝试从皮肤目录加载图标
        import os
        icon_path = "skins/default/idle/idle_000.png"
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            # 缩放到16x16作为托盘图标
            scaled = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            return QIcon(scaled)

        # 如果没有皮肤，使用简单的默认图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(Qt.GlobalColor.darkCyan)
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()
        return QIcon(pixmap)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """托盘图标被激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_pet_visibility()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 单击也可以切换显示
            pass

    def _toggle_pet_visibility(self):
        """切换宠物显示/隐藏"""
        if self._pet_window:
            if self._pet_window.isVisible():
                self._pet_window.hide()
                self._show_action.setText("显示宠物")
            else:
                self._pet_window.show()
                self._show_action.setText("隐藏宠物")

    def set_pet_window(self, pet_window):
        """设置宠物窗口引用"""
        self._pet_window = pet_window
        # 更新菜单文本
        if pet_window and self._show_action:
            self._show_action.setText("隐藏宠物" if pet_window.isVisible() else "显示宠物")

    def show_message(self, title: str, message: str, icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information, duration: int = 3000):
        """显示托盘气泡消息"""
        if self._tray_icon:
            self._tray_icon.showMessage(title, message, icon, duration)

    def update_icon(self, icon_path: str):
        """更新托盘图标"""
        if self._tray_icon:
            self._tray_icon.setIcon(QIcon(icon_path))

    def is_tray_visible(self) -> bool:
        """检查托盘图标是否可见"""
        return self._is_visible and self._tray_icon is not None

    def hide(self):
        """隐藏托盘图标"""
        if self._tray_icon:
            self._tray_icon.hide()
            self._is_visible = False

    def show(self):
        """显示托盘图标"""
        if self._tray_icon:
            self._tray_icon.show()
            self._is_visible = True

    def cleanup(self):
        """清理托盘资源"""
        if self._tray_icon:
            self._tray_icon.deleteLater()
            self._tray_icon = None
        self._is_visible = False