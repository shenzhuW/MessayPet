# core/pet_window.py
import os
import random
import asyncio
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QDateTime, QThread
from PySide6.QtGui import QPainter, QPixmap
from core.physics import PhysicsEngine
from core.event_bus import EventBus, EventType
from core.animation.state_machine import AnimationStateMachine
from core.animation.skin_manager import SkinManager
from core.window_interaction.window_interaction_manager import WindowInteractionManager
from core.window_interaction.window_monitor import WindowMonitor
from core.random_walker import RandomWalker
from core.emotion import EmotionState
from ui.context_menu import ContextMenu
from ui.widgets.chat_bubble import ChatBubble
from systems.ai.behavior_engine import BehaviorEngine
from systems.ai.llm_client import LLMClient, ClaudeCLIClient, create_llm_client
from core.config import LLMConfig
from systems.ai.memory_manager import MemoryManager
from systems.ai.emotion_analyzer import EmotionAnalyzer
from systems.ai.action_decider import ActionDecider
from core.action_history import ActionHistory
from core.work_tracker import WorkTracker
from ui.chat_dialog import ChatDialog


class PetWindow(QWidget):
    position_changed = Signal(int, int)
    action_decided = Signal(object)  # 动作决策信号，在主线程触发

    def __init__(self, config_manager, animation_manager, stat_manager=None, event_bus=None, window_tracker=None, llm_client=None, window_interaction_manager=None):
        super().__init__()
        self.config_manager = config_manager
        self.animation_manager = animation_manager
        self.stat_manager = stat_manager
        self.physics = PhysicsEngine()
        self.window_tracker = window_tracker

        # EventBus with dependency injection
        self.event_bus = event_bus or EventBus()

        # WindowInteractionManager - 统一的窗口交互管理器 (暂时禁用)
        self._window_interaction = window_interaction_manager
        # if self._window_interaction is None:
        #     # 如果没有提供，则创建一个新的
        #     self._window_interaction = WindowInteractionManager(
        #         pet_size=(64, 64),
        #         event_bus=self.event_bus
        #     )
        #     self._window_interaction.set_position_callback(self.move_to_target)
        #     self._window_interaction.start()

        # Animation state machine (必须在加载皮肤之前)
        self._state_machine = AnimationStateMachine()
        self._state_machine.on_state_change(self._on_animation_state_change)

        # Skin manager for loading animations from skins
        self.skin_manager = SkinManager()
        self._current_skin_path = ""  # 缓存当前皮肤路径
        self._load_default_skin()

        # RandomWalker - 随机移动管理器
        screen = QApplication.primaryScreen()
        if screen:
            # 使用 availableGeometry 排除任务栏等系统窗口区域
            screen_rect = screen.availableGeometry()
            self._random_walker = RandomWalker(
                pet_size=(64, 64),
                screen_width=screen_rect.width(),
                screen_height=screen_rect.height(),
                screen_x=screen_rect.x(),
                screen_y=screen_rect.y()
            )
            # 加载保存的动作速度配置（移动速度）
            saved_speeds = self.config_manager.load_action_speeds()
            if saved_speeds:
                self._random_walker.set_action_speeds(saved_speeds)
            self._random_walker.set_position_callback(self.move_to_target)
            self._random_walker.set_animation_callback(self._on_walker_animation)
            # 连接动画循环回调（用于状态动作的循环计数）
            self.animation_manager._on_loop_complete = self._random_walker._on_animation_loop
            # 注意：不再调用 start()，等待 ActionDecider 决策后执行
        else:
            self._random_walker = None

        # 加载动作帧率配置（动画播放速度）
        saved_frame_speeds = self.config_manager.load_action_frame_speeds()
        if saved_frame_speeds:
            self.animation_manager.set_action_frame_speeds(saved_frame_speeds)

        # 工作记录器
        self._work_tracker = WorkTracker(self.config_manager, self.event_bus)

        # 无边框透明窗口设置（使用 Tool 类型避免焦点切换时消失）
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 加载保存的位置
        x, y = self.config_manager.load_position()
        self.move(x, y)
        # 加载宠物大小
        pet_width, pet_height = self.config_manager.load_pet_size()
        self._pet_size = (pet_width, pet_height)
        self.setFixedSize(pet_width, pet_height)
        self.physics.set_position(x, y)
        self.physics.set_size(pet_width, pet_height)
        # 更新 RandomWalker 的宠物大小
        if self._random_walker:
            self._random_walker.set_position(x, y)
            self._random_walker.pet_size = (pet_width, pet_height)

        # 气泡提示
        self.chat_bubble = ChatBubble()

        # 行为引擎 - 根据宠物等级初始化
        pet_level = stat_manager.level if stat_manager else 1
        self.behavior_engine = BehaviorEngine(level=pet_level, event_bus=self.event_bus)

        # 记忆管理器
        self.memory_manager = MemoryManager()

        # LLM 客户端
        if llm_client:
            self.llm_client = llm_client
        else:
            llm_config = LLMConfig()
            self.llm_client = LLMClient(llm_config)
        self._chat_in_progress = False
        self._chat_cancelled = False

        # 窗口监控器
        self._window_monitor = WindowMonitor(self.event_bus)

        # 情绪状态
        self._emotion_state = EmotionState()

        # 方向追踪（用于方向性动画）
        self._last_x = x
        self._facing = "right"  # 默认朝右

        # LLM 情绪分析器（统一生成气泡）
        self._emotion_analyzer = EmotionAnalyzer(
            llm_client=self.llm_client,
            memory_manager=self.memory_manager,
            stat_manager=self.stat_manager,
            window_monitor=self._window_monitor,
            event_bus=self.event_bus
        )
        # 连接气泡信号到显示方法
        self._emotion_analyzer.bubble_ready.connect(self._show_behavior)

        # LLM 动作决策器
        self._action_history = ActionHistory(max_size=10)
        self._action_decider = ActionDecider(
            llm_client=self.llm_client,
            skin_manager=self.skin_manager,
            stat_manager=self.stat_manager,
            action_history=self._action_history,
            memory_manager=self.memory_manager
        )

        # 连接动作决策信号到槽（在主线程执行）
        self.action_decided.connect(self._on_action_decided_signal)

        # 动作完成回调
        if self._random_walker:
            self._random_walker.set_action_complete_callback(self._on_action_complete)

        # 右键菜单（需要在 emotion_analyzer 之后初始化）
        self.context_menu = ContextMenu(stat_manager, config_manager, window_tracker,
                                        emotion_analyzer=self._emotion_analyzer, parent=self)

        # 间隔设置（需要在定时器之前初始化）
        self._interval_settings = config_manager.load_interval_settings()

        # 随机触发定时器（1-5 分钟）
        self._random_trigger_timer = QTimer()
        self._random_trigger_timer.timeout.connect(self._on_random_trigger)
        self._schedule_random_trigger()

        # 单击延迟定时器（等待双击确认）
        self._click_timer = QTimer()
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_click_timeout)
        self._pending_click = False
        self._last_click_time = 0

        # 拖拽状态
        self._is_dragging = False
        self._is_executing_action = False  # 防止动作执行重入
        self._is_in_idle_wait = False  # 是否处于 idle 等待阶段（动作完成后必须等待）
        self._remaining_idle_time = 0  # idle 等待剩余时间（掉落恢复时继续等待）
        self._was_dragged = False  # 是否真正发生了拖拽
        self._drag_start_pos = QPoint()
        self._last_drag_pos = QPoint()
        self._drag_offset = QPoint()
        self._drag_velocity = (0, 0)
        self._pending_click_event = False  # 待处理的单击事件
        self._drag_start_y = 0

        # 三击检测（打开 GenericAgent 窗口）
        self._tripple_click_count = 0
        self._last_click_time = 0
        self._tripple_click_timer = QTimer()
        self._tripple_click_timer.setSingleShot(True)

        # Hook 通知状态追踪（用于判断是否要覆盖当前气泡）
        self._current_hook_status = None  # 当前显示的hook状态
        self._tripple_click_timer.timeout.connect(self._reset_tripple_click)

        # 落地动画状态
        self._is_playing_land_animation = False
        self._load_land_animation()

        # 防止重复触发 idle 等待
        self._idle_wait_pending = False

        # 窗口切换冷却时间
        self._last_window_trigger = 0
        self._window_trigger_cooldown = 5000  # 5秒冷却

        # 订阅事件
        self._subscribe_events()

        # 启动动画和物理
        self.animation_manager.start_idle_animation(self.update)
        self._physics_timer = QTimer()
        self._physics_timer.timeout.connect(self._update_physics)
        self._physics_timer.start(16)  # ~60fps

        # 启动初始动作决策（延迟 2 秒让其他初始化完成）
        QTimer.singleShot(2000, self._request_action_decision)

        # 启动工作记录器
        self._work_tracker.start()

        # Hook 通知文件监视器
        self._hook_file = os.path.join(os.path.expanduser("~"), ".deskpet", "hook_notification.txt")
        self._hook_watcher = QTimer()
        self._hook_watcher.timeout.connect(self._check_hook_notification)
        self._hook_watcher.start(2000)  # 每2秒检查一次即可，文件不常写入

    def _check_hook_notification(self):
        """检测 Claude Code hook 通知文件"""
        if os.path.exists(self._hook_file):
            try:
                with open(self._hook_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                
                # 解析状态和消息（格式: "状态|消息"）
                status = "normal"
                text = content
                if "|" in content:
                    parts = content.split("|", 1)
                    status = parts[0]
                    text = parts[1] if len(parts) > 1 else ""

                
                if text:
                    # 检查气泡是否正在锁定中
                    current_time = QDateTime.currentMSecsSinceEpoch()
                    locked_until = getattr(self.chat_bubble, '_locked_until', 0)
                    is_locked = locked_until > current_time

                    if is_locked:
                        # 气泡锁定中，强制更新文本和颜色
                        self.chat_bubble._locked_until = 0
                        self.chat_bubble.hide()

                        lock_time = current_time + 5000
                        self.chat_bubble._locked_until = lock_time
                        self._current_hook_status = status

                        # 根据状态设置颜色
                        if status == "waiting":
                            self.chat_bubble.set_waiting()
                        elif status == "complete":
                            self.chat_bubble.set_complete()
                        else:
                            self.chat_bubble.reset_border()

                        self._show_behavior(text, min_duration=5000, reset_border=False)
                    else:
                        # 气泡未锁定，显示新状态
                        # 锁定气泡 8 秒，不被替代
                        lock_time = current_time + 5000
                        self.chat_bubble._locked_until = lock_time
                        self._current_hook_status = status

                        # 根据状态设置边框颜色
                        if status == "waiting":
                            self.chat_bubble.set_waiting()
                        elif status == "complete":
                            self.chat_bubble.set_complete()
                        else:
                            self.chat_bubble.reset_border()

                        self._show_behavior(text, min_duration=5000, reset_border=False)
                os.remove(self._hook_file)
            except Exception:
                pass

    def _summarize_text(self, text: str) -> str:
        """使用 Bubble LLM 简化文本到 30 字以内"""
        if not text or len(text) <= 30:
            return text

        import httpx
        from prompts.system import build_system_prompt

        # 加载 Bubble LLM 配置
        llm_config = self.config_manager.load_llm_config()
        base_url = llm_config.get("bubble_base_url", "")
        api_key = llm_config.get("bubble_api_key", "")
        model = llm_config.get("bubble_model", "")

        # 获取人设
        system_prompt = build_system_prompt(
            pet_profile=self.memory_manager.pet_profile,
            user_profile=self.memory_manager.user_profile,
            facts=self.memory_manager.facts,
            conversation=self.memory_manager.conversation
        )

        user_prompt = f"""请将以下消息简化到30个字以内，只保留核心信息，用中文回复：
{text}
直接输出简化后的内容。
- 如果是'Read: Wait: Edit'，则提醒用户claude code在等待确认
- 如果是'Read: Claude finished'，则告知用户claude code已经完成"""

        try:
            base = base_url.rstrip('/')
            if not base.endswith('/v1'):
                base += '/v1'
            url = f"{base}/chat/completions"

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 100,
                "temperature": 0.8,
                "chat_template_kwargs": {"enable_thinking": False}
            }

            resp = httpx.post(url, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                result = resp.json()
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    content = content.strip().strip('"\'')
                    if content:
                        return content
        except Exception:
            pass
        return text[:30]

    def _load_default_skin(self):
        """Load default skin if available."""
        # 从配置加载当前皮肤
        current_skin = self.config_manager.get_current_skin()
        self._current_skin_path = f"skins/{current_skin}"
        if os.path.exists(self._current_skin_path):
            self.skin_manager.scan(self._current_skin_path)
            self.animation_manager.load_idle_sequence(self._current_skin_path)
            # 设置被动状态
            passive_actions = self.skin_manager.get_config().get("passive_actions", [])
            self._state_machine.set_passive_states(passive_actions)

    def switch_skin(self, skin_name: str):
        """切换皮肤并重新加载动画"""
        print(f"[PetWindow] switch_skin called: {skin_name}")
        skin_path = f"skins/{skin_name}"
        print(f"[PetWindow] 皮肤路径存在: {os.path.exists(skin_path)}")
        if os.path.exists(skin_path):
            self._current_skin_path = skin_path
            self.skin_manager.skin_name = skin_name
            self.skin_manager.scan(skin_path)
            # 更新状态机的被动状态
            passive_actions = self.skin_manager.get_config().get("passive_actions", [])
            self._state_machine.set_passive_states(passive_actions)
            # 清除帧缓存，确保加载新皮肤帧
            self.skin_manager._frame_cache = {}
            # 重新加载 land 动画
            self._load_land_animation()
            # 重新加载当前状态的动画
            self._on_animation_state_change(None, self._state_machine.current_state)
        else:
            print(f"[PetWindow] 皮肤路径不存在: {skin_path}")

    def set_pet_size(self, width: int, height: int):
        """设置宠物大小并保存"""
        self._pet_size = (width, height)
        self.setFixedSize(width, height)
        self.physics.set_size(width, height)
        # 更新 RandomWalker 的宠物大小
        if self._random_walker:
            self._random_walker.pet_size = (width, height)
        self.config_manager.save_pet_size(width, height)

    def _on_animation_state_change(self, old_state: str, new_state: str):
        """Handle animation state changes by loading appropriate animation frames."""
        # 直接用状态名加载动画
        if self.skin_manager.has_animation(new_state):
            direction = self._facing if self.skin_manager.is_directional(new_state) else None
            frames = self.skin_manager.load_animation_frames(new_state, direction)
            if frames:
                self.animation_manager.set_frames(frames, new_state)
        elif self.skin_manager.has_animation("idle"):
            # 没有对应动画时使用 idle
            frames = self.skin_manager.load_animation_frames("idle")
            if frames:
                self.animation_manager.set_frames(frames, "idle")

    def _load_land_animation(self):
        """加载落地/爬起动画（使用当前皮肤）"""
        current_skin = self.config_manager.get_current_skin()
        land_dir = f"skins/{current_skin}/land"
        if os.path.exists(land_dir):
            self._land_frames = []
            frame_files = sorted([
                f for f in os.listdir(land_dir)
                if f.startswith("land_") and f.endswith(".png")
            ])
            if not frame_files:
                # 检查方向变体
                for direction in ["left", "right"]:
                    direction_dir = os.path.join(land_dir, direction)
                    if os.path.exists(direction_dir):
                        frame_files = sorted([
                            f for f in os.listdir(direction_dir)
                            if f.startswith("land_") and f.endswith(".png")
                        ])
                        if frame_files:
                            land_dir = direction_dir
                            break
            from PIL import Image
            from core.animation.manager import AnimationManager
            _anim_mgr = AnimationManager()
            for frame_file in frame_files:
                img_path = os.path.join(land_dir, frame_file)
                img = Image.open(img_path)
                try:
                    img = img.convert("RGBA")
                    self._land_frames.append(_anim_mgr._pil_to_pixmap(img))
                finally:
                    img.close()
        else:
            self._land_frames = []

    def _update_physics(self):
        # 播放落地动画时不更新物理
        if self._is_playing_land_animation:
            return

        # 先更新物理位置
        if not self._is_dragging and self.physics.is_thrown:
            self.physics.update(1/60)
            self.move(*self.physics.position.to_tuple())
            self.update()

        # 检查是否触地并播放落地动画（必须在 physics.update() 之后）
        if self.physics.has_hit_ground():
            self.event_bus.publish(EventType.PET_LANDED, {
                "position": self.physics.position.to_tuple()
            })
            self._state_machine.set_state("land")

            if self._land_frames:
                self._play_land_animation()
            return

    def _play_land_animation(self):
        """播放落地动画"""
        if not self._land_frames:
            return

        self._is_playing_land_animation = True
        self._current_land_frame = 0

        # 停止当前动画，播放落地动画
        self.animation_manager.stop()

        def animate():
            if self._current_land_frame < len(self._land_frames):
                idx = self._current_land_frame
                self.animation_manager.frames = [self._land_frames[idx]]
                self.animation_manager.frame_count = 1
                self.animation_manager.current_frame_index = 0
                self.update()
                self._current_land_frame += 1
                QTimer.singleShot(100, animate)
            else:
                # 动画结束，恢复待机动画
                self.animation_manager.stop()
                self.animation_manager.load_idle_sequence(self._current_skin_path)
                self.animation_manager.start_idle_animation(self.update)
                self._is_playing_land_animation = False
                self._state_machine.set_state("idle")
                # 恢复 RandomWalker 移动
                self._resume_other_features()

        animate()

    def _play_land_animation_and_resume(self):
        """播放落地动画后恢复其他功能"""
        self.animation_manager.stop()

        if not self._land_frames:
            self._resume_other_features()
            return

        self._is_playing_land_animation = True
        self._current_land_frame = 0

        def animate():
            if self._current_land_frame < len(self._land_frames):
                idx = self._current_land_frame
                self.animation_manager.frames = [self._land_frames[idx]]
                self.animation_manager.frame_count = 1
                self.animation_manager.current_frame_index = 0
                self.update()
                self._current_land_frame += 1
                QTimer.singleShot(100, animate)
            else:
                # 动画结束，恢复待机动画
                self.animation_manager.stop()
                self.animation_manager.load_idle_sequence(self._current_skin_path)
                self.animation_manager.start_idle_animation(self.update)
                self._is_playing_land_animation = False
                self._state_machine.set_state("idle")
                self._resume_other_features()

        animate()

    def _on_idle_wait_continue(self):
        """idle 等待继续（掉落恢复后继续等待）"""
        self._remaining_idle_time = 0
        self._is_in_idle_wait = False
        self._request_action_decision()

    def _resume_other_features(self):
        """恢复其他功能（随机移动、窗口跟踪等）"""
        self.physics.set_position(self.x(), self.y())
        self._physics_timer.start()
        self.config_manager.save_position(self.x(), self.y())

        if self.window_tracker:
            self.window_tracker.set_pet_position(self.x(), self.y())
            self.window_tracker.resume()
        if self._window_interaction:
            self._window_interaction.set_pet_position(self.x(), self.y())
            self._window_interaction.resume()
        if self._random_walker:
            self._random_walker.set_position(self.x(), self.y())
            self._random_walker._external_paused = False

        # 如果处于 idle 等待阶段，继续等待剩余时间
        if self._is_in_idle_wait and self._remaining_idle_time > 0:
            remaining_secs = self._remaining_idle_time / 1000
            QTimer.singleShot(remaining_secs * 1000, self._on_idle_wait_continue)
        else:
            # 正常恢复动作决策
            QTimer.singleShot(1000, self._request_action_decision)
        self._random_walker.resume()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 使用缓存的缩放帧，避免每次重绘都缩放
        scaled = self.animation_manager.get_scaled_frame(self.size())
        if scaled and not scaled.isNull():
            painter.drawPixmap(0, 0, scaled)

    def mousePressEvent(self, event):
        # print(f"[PetWindow] mousePressEvent: button={event.button()}")
        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu.exec(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self._was_dragged = False  # 重置拖拽标志
            self._pending_click_event = True  # 标记可能有单击
            self._drag_start_pos = event.globalPosition().toPoint()
            self._last_drag_pos = self._drag_start_pos
            self._drag_start_y = self.y()
            # 记录鼠标在宠物内的偏移量
            self._drag_offset = self._drag_start_pos - QPoint(self.x(), self.y())
            self._physics_timer.stop()
            self._drag_velocity = (0, 0)
            # 按下鼠标立即切换到 held 动画
            if self.skin_manager.has_animation("held"):
                self._state_machine.set_state("held")
            # 立即暂停 random_walker，避免争夺位置
            if self._random_walker:
                self._random_walker.pause()
                self._random_walker._external_paused = True

    def mouseDoubleClickEvent(self, event):
        """双击宠物打开聊天对话框"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self._pending_click = False
            self._is_dragging = False
            self._last_click_time = QDateTime.currentMSecsSinceEpoch()

            # 使用非模态对话框，可以同时操作宠物
            dialog = ChatDialog(self.llm_client, self.stat_manager, self, self.memory_manager)
            dialog.setWindowModality(Qt.WindowModality.NonModal)
            dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)  # 聊天窗口不置顶
            dialog.show()

    def mouseMoveEvent(self, event):
        if not self._is_dragging:
            # 检查是否开始拖拽（移动超过阈值）
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self._drag_start_pos
            if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                self._is_dragging = True
                self._was_dragged = True  # 标记发生了拖拽
                self._state_machine.set_state("held")
                # 暂停窗口跟踪
                if self.window_tracker:
                    self.window_tracker.pause()
                if self._window_interaction:
                    self._window_interaction.pause()
                if self._random_walker:
                    self._random_walker.pause()
                    self._random_walker._external_paused = True

        if self._is_dragging:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self._last_drag_pos
            self._drag_velocity = (delta.x() * 2, delta.y() * 2)
            self._last_drag_pos = current_pos
            self.move(current_pos - self._drag_offset)
            self._update_bubble_position()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 计算移动距离，判断是点击还是拖拽
            drag_delta = self._last_drag_pos - self._drag_start_pos
            is_click = abs(drag_delta.x()) < 10 and abs(drag_delta.y()) < 10

            self._is_dragging = False

            # 拖拽释放不触发任何事件，只处理状态
            if self._was_dragged:
                self._was_dragged = False
            else:
                # 是单击，发布点击事件
                self.event_bus.publish(EventType.PET_CLICKED, {
                    "position": (self.x(), self.y())
                })

            if is_click:
                # 三击检测（打开 GenericAgent 窗口）
                import time
                now = time.time()
                if now - self._last_click_time < 0.5:  # 500ms 内
                    self._tripple_click_count += 1
                else:
                    self._tripple_click_count = 1
                self._last_click_time = now

                if self._tripple_click_count >= 3:
                    self._tripple_click_count = 0
                    self._tripple_click_timer.stop()
                    self._open_generic_chat()
                    return

                self._tripple_click_timer.start(500)  # 500ms 后重置计数

                # 轻轻放下 → 切换到 idle 状态
                self._state_machine.set_state("idle")
                # 延迟处理单击，等待双击确认
                self._pending_click = True
                self._click_timer.start(400)  # 400ms 内有双击则取消
                return

            # 拖拽 - 计算下落
            drag_height_diff = self._drag_start_y - self.y()
            threshold = self.physics.screen_height // 2
            if drag_height_diff > threshold:
                # 高高扔出 → 物理下落动画
                fall_velocity = min(drag_height_diff * 3, 500)
                self.physics.throw(self._drag_velocity[0], fall_velocity)
                self.physics.set_position(self.x(), self.y())
                self._physics_timer.start()  # 启动物理更新
                self.event_bus.publish(EventType.PET_THROWN, {
                    "velocity": self._drag_velocity,
                    "height_diff": drag_height_diff
                })
                self._state_machine.set_state("fall")
            else:
                # 轻轻放下 → 直接 idle
                self.physics.velocity.x = 0
                self.physics.velocity.y = 0
                self._state_machine.set_state("idle")
                self._resume_other_features()

    def closeEvent(self, event):
        self.config_manager.save_position(self.x(), self.y())
        self.animation_manager.stop()
        self._physics_timer.stop()
        # 停止工作记录器
        if self._work_tracker:
            self._work_tracker.stop()
        # 取消正在进行的聊天
        if self._chat_in_progress:
            self._chat_cancelled = True
        super().closeEvent(event)

    def move_to_target(self, x, y, direction=0.0):
        """移动到目标位置"""
        # 拖拽时不响应外部位置更新
        if self._is_dragging:
            return

        # 更新朝向（根据移动方向角度）
        # direction: 0=右, 90=上, 180=左, 270=下
        old_facing = self._facing
        if 90 < direction < 270:
            self._facing = "left"
        else:
            self._facing = "right"

        # 朝向改变时，重新加载方向性动画帧
        if old_facing != self._facing:
            current_state = self._state_machine.current_state
            if self.skin_manager.is_directional(current_state):
                frames = self.skin_manager.load_animation_frames(current_state, self._facing)
                if frames:
                    self.animation_manager.set_frames(frames, current_state)

        self.move(x, y)
        self._update_bubble_position()

    def moveEvent(self, event):
        """宠物移动时更新气泡位置"""
        super().moveEvent(event)
        self._update_bubble_position()

    def _update_bubble_position(self):
        """更新气泡跟随宠物位置"""
        if self.chat_bubble.isVisible():
            # 气泡在宠物上方，水平居中
            pet_center_x = self.x() + self.width() // 2
            bubble_width = self.chat_bubble.width()
            bubble_x = pet_center_x - bubble_width // 2
            bubble_y = self.y() - self.chat_bubble.height() - 7
            self.chat_bubble.move(int(bubble_x), int(max(0, bubble_y)))

    def _subscribe_events(self):
        """订阅事件"""
        self.event_bus.subscribe(EventType.PET_CLICKED, self._on_pet_interaction)
        self.event_bus.subscribe(EventType.WINDOW_CHANGED, self._on_window_changed)
        self.event_bus.subscribe(EventType.STAT_CHANGED, self._on_stat_changed)
        self.event_bus.subscribe(EventType.EMOTION_CHANGED, self._on_emotion_changed)

    def _check_and_trigger_behavior(self):
        """检查并触发随机行为（使用 AI 生成）- 已弃用，统一走 EmotionAnalyzer"""
        pass  # 此功能已迁移到 EmotionAnalyzer

    def _schedule_random_trigger(self):
        """安排下一次随机触发"""
        self._random_trigger_timer.stop()
        min_interval = self._interval_settings.get("bubble_min_interval", 60)
        max_interval = self._interval_settings.get("bubble_max_interval", 300)
        interval = random.randint(min_interval, max_interval) * 1000
        self._random_trigger_timer.start(interval)

    def _on_random_trigger(self):
        """随机触发情绪分析和气泡"""
        self._random_trigger_timer.stop()

        # 检查气泡是否被锁定（hook 通知正在显示），如果是则跳过
        from PySide6.QtCore import QDateTime
        current_time = QDateTime.currentMSecsSinceEpoch()
        locked_until = getattr(self.chat_bubble, '_locked_until', 0)
        is_locked = locked_until > current_time

        if is_locked:
            self._schedule_random_trigger()
            return

        self._emotion_analyzer.analyze_and_generate(trigger_type="random")

        # 安排下一次随机触发
        self._schedule_random_trigger()

    def _show_behavior(self, text: str, min_duration: int = 4000, reset_border: bool = True, reset_timer: bool = True):
        """显示行为气泡
        Args:
            text: 显示的文字
            min_duration: 最小显示时间（毫秒），Hook 通知需要至少 5000ms
            reset_border: 是否重置边框颜色（hook 通知不需要重置）
            reset_timer: 是否重置随机触发定时器
        """
        from PySide6.QtCore import QDateTime
        current_time = QDateTime.currentMSecsSinceEpoch()
        locked_until = getattr(self.chat_bubble, '_locked_until', 0)
        is_locked = locked_until > current_time

        # 如果气泡被锁定且尚未到期，不重置边框（保持 hook 通知的颜色）
        # 但如果气泡已隐藏，说明之前的 hook 已结束，应该恢复正常
        if reset_border:
            if not is_locked or not self.chat_bubble.isVisible():
                self.chat_bubble.reset_border()
        self.chat_bubble.show_text(text, duration=min_duration)
        self._update_bubble_position()
        # 非随机触发后，重置定时器
        if reset_timer:
            self._schedule_random_trigger()

    def _play_behavior_animation(self, behavior):
        """播放行为动画"""
        trigger = behavior.trigger.value if hasattr(behavior.trigger, 'value') else str(behavior.trigger)
        if trigger == "stat_low":
            if self.skin_manager.has_animation("sad"):
                self._state_machine.set_state("sad")
                QTimer.singleShot(3000, lambda: self._state_machine.set_state("idle"))
        elif "greet" in behavior.id or "chat" in behavior.id or "empathy" in behavior.id:
            if self.skin_manager.has_animation("happy"):
                self._state_machine.set_state("happy")
                QTimer.singleShot(3000, lambda: self._state_machine.set_state("idle"))

    # ========== LLM 动作决策 ==========

    def _request_action_decision(self):
        """请求 LLM 决定下一个动作（异步）"""
        if not self._action_decider:
            return

        # 正在执行动作时不发起新决策
        if self._is_executing_action:
            return

        # 处于 idle 等待阶段时不发起新决策（必须等待 idle 阶段结束）
        if self._is_in_idle_wait:
            return

        # 拖拽时不执行新动作，但保持调度以便结束后继续
        if self._is_dragging:
            QTimer.singleShot(1000, self._request_action_decision)
            return

        self._action_decider.decide_next_action(callback=self._on_action_decided)

    def _on_action_decided(self, result):
        """动作决策结果回调（在子线程中调用，发送信号到主线程）"""
        # print(f"[PetWindow] _on_action_decided: result={result}")
        # 通过信号传递结果，信号会在主线程触发槽函数
        self.action_decided.emit(result)

    def _on_action_decided_signal(self, result):
        """动作决策信号槽（在主线程执行）"""
        if result:
            # 标记正在执行动作
            self._is_executing_action = True
            self._execute_action(result)

            action = result.action
            if action in self._action_decider.MOVING_ACTIONS:
                # 移动动作用 duration（秒）控制
                QTimer.singleShot(result.duration * 1000, self._start_idle_wait)
            # 状态动作由 _on_action_complete 回调处理，不设置定时器
        else:
            # 决策失败，稍后重试
            QTimer.singleShot(10000, self._request_action_decision)

    def _start_idle_wait(self):
        """开始 idle 等待阶段"""
        # 防止重复触发
        if self._idle_wait_pending:
                        return
        self._idle_wait_pending = True

        
        # 进入 idle 等待阶段
        self._is_in_idle_wait = True
        self._is_executing_action = False
        # 切换到 idle 待机
        if self._random_walker:
            self._random_walker.execute_state("idle")

        # 记录剩余等待时间（用于掉落恢复后继续等待）
        min_interval = self._interval_settings.get("action_min_interval", 60)
        max_interval = self._interval_settings.get("action_max_interval", 300)
        idle_time = random.randint(min_interval, max_interval)
        self._remaining_idle_time = idle_time * 1000

        def after_idle():
            # idle 等待结束
            self._idle_wait_pending = False
            self._is_in_idle_wait = False
            self._remaining_idle_time = 0
            self._request_action_decision()

        QTimer.singleShot(idle_time * 1000, after_idle)

    def update_interval_settings(self, settings: dict):
        """更新间隔设置（从设置对话框调用）"""
        self._interval_settings.update(settings)
        
    def _execute_action(self, result):
        """执行动作决策"""
        if not result:
            return

        # 拖拽或下落时不执行新动作
        if self._is_dragging or self.physics.is_thrown:
            return

        action = result.action
        duration = result.duration

        # 记录到动作历史
        self._action_history.add(action, duration)

        # 更新当前动作
        self._random_walker.set_action(action)

        # 根据动作类型执行
        if action in self._action_decider.MOVING_ACTIONS:
            self._random_walker.execute_move(action, duration)
        else:
            self._random_walker.execute_state(action)
            if action == "idle":
                # idle 用持续时间控制
                QTimer.singleShot(int(duration * 1000), self._start_idle_wait)
            else:
                # 其他状态动作用循环次数控制（2-3次）
                loop_count = max(2, min(3, duration))
                self._random_walker.notify_action_duration(duration, loop_count=loop_count)

        # print(f"[PetWindow] 执行动作: {action}，持续 {duration} 秒")

    def _apply_action_effect(self, action: str):
        """执行动作效果（更新属性）"""
        if not self.stat_manager:
            return

        effects = {
            "eat": lambda: self.stat_manager.feed(15),
            "drink": lambda: self.stat_manager.drink(20),
            "rest": lambda: self.stat_manager.rest(),
            "run": lambda: setattr(self.stat_manager, 'mood', min(100, self.stat_manager.mood + 10)),
            "walk": lambda: setattr(self.stat_manager, 'mood', min(100, self.stat_manager.mood + 5)),
        }

        if action in effects:
            effects[action]()
            self.stat_manager.save()
            
    def _on_action_complete(self, action: str):
        """动作完成回调"""
        # 如果之前有 idle 等待在 pending，先清理
        if self._idle_wait_pending:
            self._idle_wait_pending = False
            self._is_in_idle_wait = False

        # 移动动作完成后也更新属性
        self._apply_action_effect(action)

        # 触发 idle 等待逻辑（移动动作的定时器也会调用这里）
        self._start_idle_wait()

    def _on_walker_animation(self, animation_name: str):
        """RandomWalker 触发的动画回调"""
        # 直接通过状态机切换，_on_animation_state_change 会加载动画
        self._state_machine.set_state(animation_name)

    def _on_pet_interaction(self, data):
        """宠物被点击时触发 AI 生成回复"""
        if self._is_dragging:
            return
        self._emotion_analyzer.analyze_and_generate(trigger_type="click")

    def _on_window_changed(self, data):
        """窗口切换时触发 LLM 情绪分析"""
        window_title = data.get("title", "")

        # 检查冷却时间
        import time
        now = time.time() * 1000
        if now - self._last_window_trigger < self._window_trigger_cooldown:
            return
        self._last_window_trigger = now

        # 30% 概率触发情绪分析
        if random.random() < 0.3:
                        self._emotion_analyzer.analyze_and_generate(trigger_type="window_change")

    def _reset_tripple_click(self):
        """重置三击计数"""
        self._tripple_click_count = 0

    def _open_generic_chat(self):
        """打开 GenericAgent 聊天窗口"""
        from ui.generic_chat import GenericChatDialog
        dialog = GenericChatDialog(self.llm_client, self)
        dialog.exec()

    def _on_click_timeout(self):
        """单击超时处理（确认不是双击）- 使用 AI 生成回复"""
        # 检查是否刚发生双击（500ms内）
        now = QDateTime.currentMSecsSinceEpoch()
        if now - self._last_click_time < 500:
            return  # 忽略，双击已处理

        if not self._pending_click:
            return
        self._pending_click = False

        self._emotion_analyzer.analyze_and_generate(trigger_type="click")

        self.physics.velocity.x = 0
        self.physics.velocity.y = 0
        # 如果没有正在下落，才恢复其他功能
        if not self.physics.is_thrown:
            self._resume_other_features()

    def start_chat(self, user_message: str):
        """开始聊天（异步）"""
        if self._chat_in_progress:
            return
        self._chat_in_progress = True
        self._chat_cancelled = False  # 重置取消标志

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if self._chat_cancelled:
                    return
                response = loop.run_until_complete(self.llm_client.chat_sync(user_message))
                if self._chat_cancelled:
                    return
                # 在主线程显示回复
                QTimer.singleShot(0, lambda: self._show_behavior(response))
            finally:
                loop.close()
                self._chat_in_progress = False

        import threading
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    def _on_stat_changed(self, data):
        """属性变化时触发 AI 关怀"""
        if not data or 'stat' not in data:
            return

        stat_name = data['stat']
        stats = self.stat_manager.get_stats() if self.stat_manager else {}
        value = stats.get(stat_name, 100)

        if value < 50:
            self._emotion_analyzer.analyze_and_generate(trigger_type="click")

    def _on_emotion_changed(self, data):
        """情绪变化时更新动画状态"""
        if not data:
            return

        emotion = data.get("emotion", "neutral")
        intensity = data.get("intensity", 0.5)

        # 更新情绪状态
        self._emotion_state.update_from_analysis(
            emotion,
            intensity,
            data.get("reason", "")
        )

        # 只在非动作执行状态下才更新动画状态
        # 防止情绪变化打断正在播放的动作动画（如 walk、qq 等）
        if self._is_executing_action:
            return

        target_state = self._emotion_state.get_animation_state()
        self._state_machine.set_state(target_state)

        # print(f"[PetWindow] Emotion changed: {emotion} (intensity: {intensity})")