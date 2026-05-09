# core/physics.py
import math
from dataclasses import dataclass
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect


@dataclass
class Vector2D:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float):
        return Vector2D(self.x * scalar, self.y * scalar)

    def __eq__(self, other):
        return math.isclose(self.x, other.x) and math.isclose(self.y, other.y)

    def __abs__(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def to_tuple(self):
        return (int(self.x), int(self.y))


def get_screen_geometry() -> QRect:
    """获取主屏幕尺寸"""
    app = QApplication.instance()
    if app:
        return app.primaryScreen().geometry()
    return QRect(0, 0, 1920, 1080)


def get_work_area_height() -> int:
    """获取工作区高度（屏幕高度减去任务栏）"""
    app = QApplication.instance()
    if app:
        screen = app.primaryScreen()
        if screen:
            return screen.availableGeometry().height()
    return get_screen_geometry().height()


class PhysicsEngine:
    GRAVITY = 600  # 像素/秒²（下落速度）
    BOUNCE = 0.3
    FRICTION = 0.98
    MAX_VELOCITY = 2000

    def __init__(self, screen_width: int = None, screen_height: int = None):
        if screen_width is None or screen_height is None:
            screen = get_screen_geometry()
            self.screen_width = screen.width()
            # 使用工作区高度而不是屏幕高度（任务栏上方）
            self.screen_height = get_work_area_height()
        else:
            self.screen_width = screen_width
            self.screen_height = screen_height

        self.position = Vector2D(0, 0)
        self.velocity = Vector2D(0, 0)
        self.size = (100, 100)
        self.is_thrown = False
        self._hit_ground = False
        self._hit_wall = False

    def set_position(self, x: int, y: int):
        self.position = Vector2D(x, y)

    def set_size(self, width: int, height: int):
        self.size = (width, height)

    def throw(self, vx: float, vy: float):
        """投掷"""
        self.velocity = Vector2D(
            max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, vx)),
            max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, vy))
        )
        self.is_thrown = True
        self._hit_ground = False
        self._hit_wall = False

    def update(self, dt: float = 1/60):
        """更新物理状态"""
        if not self.is_thrown:
            return

        # 应用重力
        self.velocity.y += self.GRAVITY * dt

        # 更新位置
        self.position = self.position + self.velocity * dt

        # 应用摩擦力
        self._apply_friction()

        # 边界检测
        self._check_bounds()

    def _apply_friction(self):
        """Apply friction to horizontal velocity only (not vertical/gravity)."""
        self.velocity.x *= self.FRICTION
        if abs(self.velocity.x) < 0.1:
            self.velocity.x = 0

    def _check_bounds(self):
        """Boundary detection with wall/ground tracking."""
        w, h = self.size
        self._hit_ground = False
        self._hit_wall = False

        # Bottom boundary
        if self.position.y + h > self.screen_height:
            self.position.y = self.screen_height - h
            self.velocity.y = 0
            self.velocity.x = 0
            self.is_thrown = False
            self._hit_ground = True

        # Top boundary
        if self.position.y < 0:
            self.position.y = 0
            self.velocity.y = max(0, self.velocity.y)

        # Right boundary with bounce
        if self.position.x + w > self.screen_width:
            self.position.x = self.screen_width - w
            self.velocity.x *= -self.BOUNCE
            if abs(self.velocity.x) < 20:
                self.velocity.x = 0
            self._hit_wall = True

        # Left boundary with bounce
        if self.position.x < 0:
            self.position.x = 0
            self.velocity.x *= -self.BOUNCE
            if abs(self.velocity.x) < 20:
                self.velocity.x = 0
            self._hit_wall = True

    def has_hit_ground(self) -> bool:
        """Whether the pet just hit the ground."""
        if self._hit_ground:
            self._hit_ground = False
            return True
        return False

    def has_hit_wall(self) -> bool:
        """Whether the pet just hit a wall."""
        if self._hit_wall:
            self._hit_wall = False
            return True
        return False