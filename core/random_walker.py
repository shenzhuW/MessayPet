# core/random_walker.py
"""移动执行器 - 宠物移动和避障"""
import math
import random
import time
from typing import Callable, Optional, Tuple
from PySide6.QtCore import QTimer


class RandomWalker:
    """宠物移动执行器 - 由 ActionDecider 决策，本类只负责执行"""

    # 默认动作速度配置
    DEFAULT_ACTION_SPEEDS = {
        "idle": 0,
        "crawl": {"speed": 1.0, "display": "慢速"},
        "walk": {"speed": 2.0, "display": "中速"},
        "run": {"speed": 4.0, "display": "快速"},
    }

    def __init__(self, pet_size: Tuple[int, int], screen_width: int, screen_height: int, screen_x: int = 0, screen_y: int = 0):
        self.pet_size = pet_size
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen_x = screen_x  # 可用区域起点 X
        self.screen_y = screen_y  # 可用区域起点 Y

        # 状态
        self._is_running = False
        self._is_paused = False
        self._external_paused = False  # 外部控制暂停（如坠落）
        self._current_action = "idle"
        self._direction = 0.0  # 角度 (0-360)

        # 位置
        self._x = 0
        self._y = 0
        self._move_start_time = 0  # 开始移动的时间
        self._move_duration = 0  # 移动持续时间（秒）

        # 定时器
        self._move_timer: Optional[QTimer] = None

        # 回调
        self._position_callback: Optional[Callable] = None
        self._animation_callback: Optional[Callable] = None
        self._action_complete_callback: Optional[Callable] = None

        # 配置的动作速度
        self._action_speeds = self.DEFAULT_ACTION_SPEEDS.copy()

        # 动画循环计数
        self._target_loops = 0
        self._current_loops = 0

    # ========== 回调设置 ==========

    def set_position_callback(self, callback: Callable[[int, int, float], None]):
        """设置位置更新回调（包含方向角度）"""
        self._position_callback = callback

    def set_animation_callback(self, callback: Callable[[str], None]):
        """设置动画切换回调"""
        self._animation_callback = callback

    def set_action_complete_callback(self, callback: Callable[[str], None]):
        """设置动作完成回调"""
        self._action_complete_callback = callback

    # ========== 位置设置 ==========

    def set_position(self, x: int, y: int):
        """设置宠物当前位置"""
        self._x = x
        self._y = y

    def set_action_speeds(self, speeds: dict):
        """设置动作速度配置"""
        self._action_speeds.update(speeds)
        self._action_speeds["idle"] = 0  # idle 永远不移动

    # ========== 执行器方法 ==========

    def execute_move(self, action: str, duration: float):
        """执行移动动作（随机方向，自动避障）

        Args:
            action: 移动动作名称（walk, run, crawl）
            duration: 持续时间（秒）
        """
        self._is_paused = False
        self._current_action = action
        self._move_duration = duration
        self._move_start_time = time.time()

        # 随机化方向（如果当前不在边缘）
        self._randomize_direction()

        # 触发动画回调
        if self._animation_callback:
            self._animation_callback(action)

        # 启动移动
        self._start_moving()

    def execute_state(self, action: str):
        """执行状态动作（暂停移动）

        Args:
            action: 状态动作名称（idle, eat, rest, happy 等）
        """
        self._is_paused = True
        self._current_action = action
        self._stop_moving()
        print(f"[RandomWalker] execute_state: {action}, target_loops={getattr(self, '_target_loops', 'N/A')}")

        # 触发动画回调
        if self._animation_callback:
            self._animation_callback(action)

    def notify_action_duration(self, duration: float, loop_count: int = None):
        """通知动作持续时间（用于状态动作）

        Args:
            duration: 移动动作的持续时间（秒），或状态动作的循环次数
            loop_count: 状态动作的循环次数，如果为 None 则用 duration 作为循环次数
        """
        # 状态动作：用循环次数控制
        if loop_count is not None:
            self._target_loops = loop_count
            self._current_loops = 0
            # 通过动画回调触发计数
            # 注意：需要外部在每次动画循环结束时调用 _on_animation_loop()
            return

        # 移动动作：用时间控制
        def on_complete():
            if self._action_complete_callback:
                self._action_complete_callback(self._current_action)
        QTimer.singleShot(int(duration * 1000), on_complete)

    def _on_animation_loop(self):
        """动画循环一次完成（由 AnimationManager 调用）"""
        if hasattr(self, '_target_loops') and self._target_loops > 0:
            self._current_loops += 1
            print(f"[RandomWalker] Animation loop: {self._current_loops}/{self._target_loops} (action: {self._current_action})")
            if self._current_loops >= self._target_loops:
                self._target_loops = 0
                self._current_loops = 0
                print(f"[RandomWalker] Animation complete, triggering callback")
                if self._action_complete_callback:
                    self._action_complete_callback(self._current_action)

    # ========== 内部方法 ==========

    def _start_moving(self):
        """启动移动"""
        if not self._is_running:
            self._is_running = True
            if self._move_timer is None:
                self._move_timer = QTimer()
                self._move_timer.timeout.connect(self._update_position)
            self._move_timer.start(16)  # ~60fps

    def _stop_moving(self):
        """停止移动"""
        self._is_running = False
        if self._move_timer:
            self._move_timer.stop()

    def _randomize_direction(self):
        """随机化移动方向"""
        self._direction = random.uniform(0, 360)

    def _update_position(self):
        """更新位置"""
        if not self._is_running or self._is_paused:
            return

        # 外部暂停（如坠落）
        if self._external_paused:
            return

        # 检查是否达到持续时间
        elapsed = time.time() - self._move_start_time
        if elapsed >= self._move_duration:
            self._on_action_complete()
            return

        # 获取速度
        action_speed = self._action_speeds.get(self._current_action, {})
        speed = action_speed.get("speed", 0) if isinstance(action_speed, dict) else action_speed

        if speed == 0:
            return

        # 计算新位置
        rad = math.radians(self._direction)
        new_x = self._x + int(speed * math.cos(rad))
        new_y = self._y + int(speed * math.sin(rad))

        # 边界检测
        margin = 10
        min_x = self.screen_x + margin
        max_x = self.screen_x + self.screen_width - self.pet_size[0] - margin
        min_y = self.screen_y + margin
        max_y = self.screen_y + self.screen_height - self.pet_size[1] - margin

        # 边缘碰撞 - 随机转向并重新计算位置
        if new_x < min_x or new_x > max_x or new_y < min_y or new_y > max_y:
            self._direction = random.uniform(0, 360)
            rad = math.radians(self._direction)
            new_x = self._x + int(speed * math.cos(rad))
            new_y = self._y + int(speed * math.sin(rad))

            # 如果新方向仍然越界，直接修正到边界内
            if new_x < min_x:
                new_x = min_x
            if new_x > max_x:
                new_x = max_x
            if new_y < min_y:
                new_y = min_y
            if new_y > max_y:
                new_y = max_y

        # 更新位置
        self._x = new_x
        self._y = new_y

        if self._position_callback:
            self._position_callback(self._x, self._y, self._direction)

    def _on_edge_hit(self):
        """边缘碰撞处理 - 朝向屏幕中心转向"""
        center_x = self.screen_x + self.screen_width // 2
        center_y = self.screen_y + self.screen_height // 2
        self._direction = math.degrees(math.atan2(center_y - self._y, center_x - self._x))

    def _on_action_complete(self):
        """动作完成"""
        self._stop_moving()
        if self._action_complete_callback:
            self._action_complete_callback(self._current_action)

    # ========== 兼容方法 ==========

    def start(self):
        """兼容旧代码 - 启动（不再自动随机选择动作）"""
        pass

    def stop(self):
        """停止移动"""
        self._stop_moving()

    def pause(self):
        """暂停移动（用户拖拽时）"""
        self._is_paused = True

    def resume(self):
        """恢复移动（延迟2秒）- 兼容旧代码"""
        def delayed_resume():
            self._is_paused = False
        QTimer.singleShot(2000, delayed_resume)

    def is_moving(self) -> bool:
        """是否正在移动"""
        return self._is_running and not self._is_paused

    @property
    def current_action(self) -> str:
        """获取当前动作"""
        return self._current_action

    def set_action(self, action: str):
        """设置当前动作"""
        self._current_action = action