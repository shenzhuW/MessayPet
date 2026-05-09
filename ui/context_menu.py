# ui/context_menu.py
import os
from PySide6.QtWidgets import QMenu, QWidgetAction, QLabel, QProgressBar, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import webbrowser


PIXEL_FONT = "Courier New"
# 星露谷明亮调色板
PIXEL_BG = "rgba(245, 240, 225, 250)"        # 奶油白
PIXEL_BORDER = "#8b6914"                     # 麦秆金边框
PIXEL_BORDER_DARK = "#5d4037"                # 深木棕
PIXEL_SELECTED = "#ffcd75"                   # 金麦色选中
PIXEL_TEXT = "#3f2f25"                       # 深木色文字
PIXEL_ACCENT = "#b86f32"                     # 暖橙强调
PIXEL_BAR_BG = "#d4c8a8"                     # 浅麦色
PIXEL_BAR_GREEN = "#5a9c32"                  # 草地绿
PIXEL_BAR_YELLOW = "#e8a832"                 # 琥珀黄
PIXEL_BAR_RED = "#c44040"                    # 番茄红


class ContextMenu(QMenu):
    def __init__(self, stat_manager, config_manager, window_tracker=None, emotion_analyzer=None, parent=None):
        super().__init__(parent)
        self.stat_manager = stat_manager
        self.config_manager = config_manager
        self.window_tracker = window_tracker
        self._emotion_analyzer = emotion_analyzer

        self.setStyleSheet(f"""
            QMenu {{
                background-color: {PIXEL_BG};
                border: 3px solid {PIXEL_BORDER};
                padding: 4px;
                font-family: "{PIXEL_FONT}";
                font-size: 12px;
            }}
            QMenu::item {{
                color: {PIXEL_TEXT};
                padding: 5px 20px 5px 8px;
                border: 1px solid transparent;
            }}
            QMenu::item:selected {{
                background-color: {PIXEL_SELECTED};
                border: 1px solid {PIXEL_BORDER_DARK};
            }}
            QMenu::separator {{
                height: 2px;
                background-color: {PIXEL_BORDER};
                margin: 4px 4px;
            }}
        """)

        self._build_menu()

    def showEvent(self, event):
        """菜单显示时刷新属性"""
        self._refresh_stats()
        super().showEvent(event)

    def _refresh_stats(self):
        """刷新属性子菜单"""
        stats = self.stat_manager.get_stats()
        stat_items = [
            ("饱食度", stats["hunger"]),
            ("心情", stats["mood"]),
            ("健康", stats["health"]),
            ("活力", stats["energy"]),
        ]

        for i, (stat_name, stat_value) in enumerate(stat_items):
            if i < len(self._attr_menu.actions()):
                action = self._attr_menu.actions()[i]
                widget = action.defaultWidget()
                if widget:
                    layout = widget.layout()
                    if layout and layout.count() >= 3:
                        bar = layout.itemAt(1).widget()
                        value_label = layout.itemAt(2).widget()
                        if isinstance(bar, QProgressBar) and isinstance(value_label, QLabel):
                            bar.setValue(stat_value)
                            value_label.setText(f"{stat_value}")

    def _build_menu(self):
        # 属性
        self._attr_menu = self.addMenu("属性")
        self._add_stat_display(self._attr_menu)

        # 互动
        interact_action = self.addMenu("互动")
        self._add_interaction_actions(interact_action)

        # 功能
        function_action = self.addMenu("功能")
        self._add_function_actions(function_action)

        self.addSeparator()

        # 编辑角色卡
        edit_profile_action = self.addAction("编辑角色卡")
        edit_profile_action.triggered.connect(self._on_open_profile_editor)

        self.addSeparator()

        # 设置
        settings_action = self.addAction("设置...")
        settings_action.triggered.connect(self._on_open_settings)

        self.addSeparator()

        # 退出
        quit_action = self.addAction("退出")
        quit_action.triggered.connect(self._on_quit)

    def _add_stat_display(self, menu: QMenu):
        stats = self.stat_manager.get_stats()

        for stat_name, stat_value in [("饱食度", stats["hunger"]),
                                        ("心情", stats["mood"]),
                                        ("健康", stats["health"]),
                                        ("活力", stats["energy"]),
                                        ("年龄", stats["age"])]:
            action = QWidgetAction(menu)
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)

            label = QLabel(stat_name)
            label.setFixedWidth(60)
            label.setStyleSheet(f"color: {PIXEL_TEXT}; font-family: '{PIXEL_FONT}'; font-size: 12px;")
            layout.addWidget(label)

            bar = QProgressBar()
            bar.setValue(stat_value)
            bar.setFixedWidth(100)
            bar.setFixedHeight(8)
            bar.setTextVisible(False)

            bar_color = PIXEL_BAR_GREEN
            if stat_value < 30:
                bar_color = PIXEL_BAR_RED
            elif stat_value < 60:
                bar_color = PIXEL_BAR_YELLOW

            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid {PIXEL_BORDER};
                    background-color: {PIXEL_BAR_BG};
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color};
                }}
            """)
            layout.addWidget(bar)

            value_label = QLabel(f"{stat_value}")
            value_label.setFixedWidth(30)
            value_label.setStyleSheet(f"color: {PIXEL_TEXT}; font-family: '{PIXEL_FONT}'; font-size: 12px;")
            layout.addWidget(value_label)

            widget.setLayout(layout)
            action.setDefaultWidget(widget)
            menu.addAction(action)

    def _add_web_shortcuts(self, menu: QMenu):
        shortcuts = self.config_manager.load_web_shortcuts()
        if not shortcuts:
            empty_action = menu.addAction("（未设置快捷方式）")
            empty_action.setEnabled(False)
            return

        for shortcut in shortcuts:
            action = menu.addAction(shortcut.get("name", "未命名"))
            url = shortcut.get("url")
            if url:
                action.triggered.connect(lambda _, u=url: webbrowser.open(u))

    def _add_interaction_actions(self, menu: QMenu):
        """添加互动子菜单"""
        feed_action = menu.addAction("喂食 🍎")
        feed_action.triggered.connect(self._on_feed)

        play_action = menu.addAction("玩耍 🎮")
        play_action.triggered.connect(self._on_play)

        rest_action = menu.addAction("休息 💤")
        rest_action.triggered.connect(self._on_rest)

    def _on_feed(self):
        self.stat_manager.feed()
        self.stat_manager.save()
        self._trigger_interaction_bubble("喂食")

    def _on_play(self):
        self.stat_manager.play()
        self.stat_manager.save()
        self._trigger_interaction_bubble("玩耍")

    def _on_rest(self):
        self.stat_manager.rest()
        self.stat_manager.save()
        self._trigger_interaction_bubble("休息")

    def _trigger_interaction_bubble(self, action_type: str):
        """触发互动气泡"""
        if self._emotion_analyzer:
            self._emotion_analyzer.analyze_and_generate(trigger_type="interaction", interaction=action_type)

    def _add_function_actions(self, menu: QMenu):
        """添加功能子菜单"""
        work_stats_action = menu.addAction("工时统计")
        work_stats_action.triggered.connect(self._on_open_work_stats)

        # 快速打开子菜单
        quick_open_menu = menu.addMenu("快速打开")
        self._add_quick_open_actions(quick_open_menu)

    def _add_quick_open_actions(self, menu: QMenu):
        """添加快速打开的网页快捷方式"""
        shortcuts = self.config_manager.load_web_shortcuts()
        if not shortcuts:
            empty_action = menu.addAction("（未设置快捷方式）")
            empty_action.setEnabled(False)
            return

        for shortcut in shortcuts:
            action = menu.addAction(shortcut.get("name", "未命名"))
            url = shortcut.get("url")
            if url:
                action.triggered.connect(lambda _, u=url: webbrowser.open(u))

    def _on_open_work_stats(self):
        """打开工时统计页面"""
        from core.pet_window import PetWindow
        parent = self.parent()
        if isinstance(parent, PetWindow) and hasattr(parent, '_work_tracker'):
            work_tracker = parent._work_tracker
            self._generate_and_open_stats_page(work_tracker)

    def _generate_and_open_stats_page(self, work_tracker):
        """生成统计页面并用浏览器打开"""
        import json
        import tempfile
        import webbrowser
        from datetime import datetime

        # 获取数据
        records = work_tracker.config_manager.load_work_records()

        # 读取 HTML 模板
        template_path = "templates/work_stats.html"
        if not os.path.exists(template_path):
            # 尝试从脚本目录
            import sys
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_path = os.path.join(base_dir, "templates", "work_stats.html")

        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()

        # 替换数据
        data_json = json.dumps(records, ensure_ascii=False)
        html = html.replace("{{WORK_DATA}}", data_json)

        # 保存到临时文件
        temp_file = os.path.join(tempfile.gettempdir(), "deskpet_work_stats.html")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(html)

        # 用浏览器打开
        webbrowser.open(f"file:///{temp_file}")

    def _on_open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config_manager, self)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.show()
        # 非模态对话框不需要等待关闭，宠物可以继续操作
        # 跟踪会在下次用户点击宠物时自动恢复

    def _on_open_profile_editor(self):
        from core.pet_window import PetWindow
        parent = self.parent()
        if isinstance(parent, PetWindow) and hasattr(parent, 'memory_manager'):
            from ui.pet_profile_editor import PetProfileEditor
            stat_manager = getattr(parent, 'stat_manager', None)
            editor = PetProfileEditor(parent.memory_manager, stat_manager, parent)
            editor.setWindowModality(Qt.WindowModality.NonModal)
            editor.show()

    def _on_quit(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()