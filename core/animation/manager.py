# core/animation.py
import os
import warnings
from typing import List, Callable, Optional
from PIL import Image, ImageSequence
from PySide6.QtCore import QTimer, QSize, Qt
from PySide6.QtGui import QPixmap, QImage


class AnimationManager:
    FRAME_RATE = 60  # 显示刷新率
    DEFAULT_FPS = 12  # 默认动画帧率

    def __init__(self):
        self.frames: List[QPixmap] = []
        self.current_frame_index = 0
        self.frame_count = 0
        self._anim_timer = QTimer()
        self._frame_duration = int(1000 / self.DEFAULT_FPS)
        self._on_update: Optional[Callable] = None
        self._is_playing = False
        self._action_connection = None
        # 每个动作的帧率配置 {"idle": 6, "walk": 12, ...}
        self._action_frame_speeds: dict = {}
        # 当前动作 ID（用于实时更新帧率）
        self._current_action_id: str = "idle"
        # 循环回调（用于状态动作的循环计数）
        self._on_loop_complete: Optional[Callable] = None

    def set_action_frame_speed(self, action_id: str, fps: int):
        """设置动作的帧率"""
        self._action_frame_speeds[action_id] = fps
        # 如果当前正在播放这个动作，立即更新间隔
        if self._is_playing and action_id == self._current_action_id:
            self._anim_timer.setInterval(self._get_frame_duration(action_id))

    def set_action_frame_speeds(self, speeds: dict):
        """批量设置动作帧率"""
        self._action_frame_speeds.update(speeds)
        # 如果定时器在运行，更新当前动作的间隔
        if self._is_playing:
            self._anim_timer.setInterval(self._get_frame_duration(self._current_action_id))

    def _get_frame_duration(self, action_id: str = None) -> int:
        """获取动作的帧间隔（毫秒）"""
        if action_id and action_id in self._action_frame_speeds:
            fps = self._action_frame_speeds[action_id]
            if fps > 0:
                return int(1000 / fps)
        return self._frame_duration

    def load_gif(self, path: str):
        """加载 GIF 动画"""
        self.frames = []
        img = Image.open(path)
        for frame in ImageSequence.Iterator(img):
            frame_rgba = frame.copy().convert("RGBA")
            pixmap = self._pil_to_pixmap(frame_rgba)
            self.frames.append(pixmap)
        self.frame_count = len(self.frames)
        self.current_frame_index = 0
        
    def load_sequence(self, folder: str, prefix: str = "frame", ext: str = ".png"):
        """加载图片序列"""
        self.frames = []
        if not os.path.exists(folder):
            return
        frame_files = sorted([
            f for f in os.listdir(folder)
            if f.startswith(prefix) and f.endswith(ext)
        ])
        for frame_file in frame_files:
            img_path = os.path.join(folder, frame_file)
            img = Image.open(img_path).convert("RGBA")
            self.frames.append(self._pil_to_pixmap(img))
            img.close()
        self.frame_count = len(self.frames)
        self.current_frame_index = 0
        
    def load_idle_sequence(self, folder: str):
        """加载待机动画，支持子目录结构（如 skins/default/idle/）"""
        idle_folder = os.path.join(folder, "idle")
        if os.path.isdir(idle_folder):
            self.load_sequence(idle_folder, prefix="idle_", ext=".png")
        else:
            self.load_sequence(folder, prefix="idle_", ext=".png")

    def _pil_to_pixmap(self, pil_image: Image.Image) -> QPixmap:
        data = pil_image.tobytes("raw", "RGBA")
        stride = pil_image.width * 4
        qimage = QImage(data, pil_image.width, pil_image.height, stride, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def get_current_frame(self) -> Optional[QPixmap]:
        if self.frames and self.frame_count > 0 and self.current_frame_index < len(self.frames):
            return self.frames[self.current_frame_index]
        return None

    def get_scaled_frame(self, size: QSize) -> Optional[QPixmap]:
        """获取缩放后的帧"""
        if not self.frames or self.current_frame_index >= len(self.frames):
            return None
        return self.frames[self.current_frame_index].scaled(
            size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

    def _advance_frame(self):
        if self.frame_count > 0:
            self.current_frame_index = (self.current_frame_index + 1) % self.frame_count

    def start_idle_animation(self, on_update: Callable):
        """启动待机动画循环"""
        # 先断开所有现有回调（抑制断开不存在的连接时的警告）
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                self._anim_timer.timeout.disconnect()
        except (TypeError, RuntimeError):
            pass

        self._on_update = on_update
        self._current_action_id = "idle"
        self._anim_timer.timeout.connect(self._tick)
        frame_duration = self._get_frame_duration("idle")
        self._anim_timer.start(frame_duration)
        self._is_playing = True

    def restart_idle_animation(self):
        """重启待机动画以应用新的帧率"""
        if self._is_playing and self._anim_timer.isActive():
            frame_duration = self._get_frame_duration("idle")
            self._anim_timer.setInterval(frame_duration)

    def _tick(self):
        was_at_last_frame = self.current_frame_index == self.frame_count - 1
        self._advance_frame()
        # 如果刚回到第一帧（完成一次循环）
        if was_at_last_frame and self.current_frame_index == 0 and self._on_loop_complete:
            self._on_loop_complete()
        if self._on_update:
            self._on_update()

    def play_action(self, frames: List[QPixmap], action_id: str = None, callback: Optional[Callable] = None):
        """播放动作动画"""
        if action_id:
            self._current_action_id = action_id

        original_frames = self.frames.copy()
        original_count = self.frame_count
        original_index = self.current_frame_index

        self.frames = frames
        self.frame_count = len(frames)
        self.current_frame_index = 0

        def on_action_end():
            self.frames = original_frames
            self.frame_count = original_count
            self.current_frame_index = original_index
            if callback:
                callback()

        # 先断开所有现有回调
        try:
            self._anim_timer.timeout.disconnect()
        except (TypeError, RuntimeError):
            pass

        frame_duration = self._get_frame_duration(action_id)
        self._action_connection = lambda: self._action_tick(on_action_end)
        self._anim_timer.timeout.connect(self._action_connection)
        self._anim_timer.setInterval(frame_duration)
        self._anim_timer.start()
        self._is_playing = True

    def _action_tick(self, on_end: Callable):
        self._advance_frame()
        if self.current_frame_index == 0 and self.frame_count > 1:
            self._anim_timer.timeout.disconnect()
            # 立即标记为已结束，防止重入
            self._action_connection = None
            on_end()
        if self._on_update:
            self._on_update()

    def stop(self):
        """停止动画"""
        self._anim_timer.stop()
        # 断开所有回调
        try:
            self._anim_timer.timeout.disconnect()
        except TypeError:
            pass
        self._action_connection = None
        self._is_playing = False

    def set_frames(self, frames: List[QPixmap], action_id: str = None):
        """设置帧并根据动作更新定时器间隔"""
        if action_id:
            self._current_action_id = action_id

        self.frames = frames
        self.frame_count = len(frames)
        self.current_frame_index = 0

        frame_duration = self._get_frame_duration(action_id)
        self._anim_timer.setInterval(frame_duration)

        # 确保定时器在运行且回调已连接
        if not self._anim_timer.isActive():
            # 先断开所有现有回调
            try:
                self._anim_timer.timeout.disconnect()
            except TypeError:
                pass
            self._anim_timer.timeout.connect(self._tick)
            self._anim_timer.start()
            self._is_playing = True