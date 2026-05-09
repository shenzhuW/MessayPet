import os
import json
from typing import Dict, List, Optional, Set, Union
from PIL import Image
from PySide6.QtGui import QPixmap, QImage

# 默认皮肤名称
DEFAULT_SKIN = "default"

# 方向变体目录名称
DIRECTION_VARIANTS = ["left", "right"]

# 默认动作分类（当皮肤没有配置时使用）
DEFAULT_MOVING_ACTIONS = {"walk", "run", "crawl"}
DEFAULT_STATE_ACTIONS = {"idle", "eat", "drink", "rest", "happy", "sad", "held", "interact", "tianmao"}

# 被动动作（由系统事件触发，不应由 LLM 决策）
DEFAULT_PASSIVE_ACTIONS = {"fall", "land", "held", "huishou"}


class SkinManager:
    """Manages skin loading and animation frame discovery."""

    def __init__(self):
        self.skin_path: Optional[str] = None
        self.skin_name: Optional[str] = None
        # 结构: {"animation_name": {"type": "normal"|"directional", "frame_count": int, "directions": {}}}
        self.available_animations: Dict[str, Dict] = {}
        self._frame_cache: Dict[str, List[QPixmap]] = {}
        # 皮肤配置
        self._config: Dict = {}

    def _count_frames(self, directory: str) -> int:
        """Count PNG/GIF files in a directory (non-recursive)."""
        return len([
            f for f in os.listdir(directory)
            if f.endswith('.png') or f.endswith('.gif')
        ])

    def scan(self, skin_path: str):
        """Scan a skin directory and discover all animation sets.

        Supports both flat structure (animation/*.png) and directional structure
        (animation/left/*.png, animation/right/*.png).
        """
        self.skin_path = skin_path
        self.available_animations = {}
        self._frame_cache = {}
        self._config = {}

        if not os.path.isdir(skin_path):
            return

        # 加载皮肤配置（如果有）
        config_path = os.path.join(skin_path, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"[SkinManager] Failed to load config: {e}")

        for entry in os.listdir(skin_path):
            entry_path = os.path.join(skin_path, entry)
            if not os.path.isdir(entry_path):
                continue

            # 检查是否为方向变体结构（同时存在 left 和 right 子目录）
            has_direction_variants = all(
                os.path.isdir(os.path.join(entry_path, direction))
                for direction in DIRECTION_VARIANTS
            )

            if has_direction_variants:
                # 方向变体结构: 统计每个方向的帧数
                directions = {}
                for direction in DIRECTION_VARIANTS:
                    dir_path = os.path.join(entry_path, direction)
                    frame_count = self._count_frames(dir_path)
                    if frame_count > 0:
                        directions[direction] = frame_count
                if directions:
                    self.available_animations[entry] = {
                        "type": "directional",
                        "frame_count": sum(directions.values()),
                        "directions": directions
                    }
            else:
                # 普通结构: 直接统计帧数
                frame_count = self._count_frames(entry_path)
                if frame_count > 0:
                    self.available_animations[entry] = {
                        "type": "normal",
                        "frame_count": frame_count,
                        "directions": {}
                    }

    def load_animation_frames(self, animation_name: str, direction: str = None) -> List[QPixmap]:
        """Load all frames for a specific animation.

        Args:
            animation_name: Name of the animation (e.g., "eat", "drink", "idle")
            direction: Optional direction ("left" or "right"). If the animation
                      has directional variants and no direction is specified,
                      defaults to "left".

        Returns:
            List of QPixmap frames for the animation.
        """
        # 确定缓存 key
        cache_key = f"{animation_name}:{direction}" if direction else animation_name
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key]

        if not self.skin_path or animation_name not in self.available_animations:
            return []

        anim_info = self.available_animations[animation_name]
        animation_dir = os.path.join(self.skin_path, animation_name)

        # 确定加载路径
        if anim_info["type"] == "directional":
            if direction and direction in anim_info["directions"]:
                animation_dir = os.path.join(animation_dir, direction)
            elif "left" in anim_info["directions"]:
                # 默认使用 left
                animation_dir = os.path.join(animation_dir, "left")
            else:
                # 回退到第一个可用方向
                first_dir = next(iter(anim_info["directions"]))
                animation_dir = os.path.join(animation_dir, first_dir)

        frame_files = sorted([
            f for f in os.listdir(animation_dir)
            if f.endswith('.png') or f.endswith('.gif')
        ])

        frames = []
        for frame_file in frame_files:
            img = Image.open(os.path.join(animation_dir, frame_file))
            try:
                img = img.convert("RGBA")
                frames.append(self._pil_to_pixmap(img))
            finally:
                img.close()

        self._frame_cache[cache_key] = frames
        return frames

    def is_directional(self, animation_name: str) -> bool:
        """Check if an animation has directional variants."""
        if animation_name not in self.available_animations:
            return False
        return self.available_animations[animation_name]["type"] == "directional"

    def get_directions(self, animation_name: str) -> List[str]:
        """Get available directions for an animation."""
        if animation_name not in self.available_animations:
            return []
        return list(self.available_animations[animation_name].get("directions", {}).keys())

    def get_animation_names(self) -> List[str]:
        return list(self.available_animations.keys())

    def has_animation(self, name: str) -> bool:
        return name in self.available_animations

    def _pil_to_pixmap(self, pil_image: Image.Image) -> QPixmap:
        data = pil_image.tobytes("raw", "RGBA")
        stride = pil_image.width * 4  # 4 bytes per pixel for RGBA
        qimage = QImage(data, pil_image.width, pil_image.height, stride, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    @staticmethod
    def get_available_skins() -> List[str]:
        """扫描 skins/ 目录，返回所有可用皮肤列表"""
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skins")
        if not os.path.isdir(base_path):
            return []

        skins = []
        for entry in os.listdir(base_path):
            entry_path = os.path.join(base_path, entry)
            if os.path.isdir(entry_path):
                skins.append(entry)
        return sorted(skins)

    @staticmethod
    def validate_skin(skin_name: str) -> Dict[str, any]:
        """验证皮肤配置是否完整

        基于 config.json 中的 moving_actions + state_actions + passive_actions
        验证对应的动作文件夹是否存在且有帧图片。

        Returns:
            {
                "valid": bool,
                "missing_required": List[str],  # 缺失的动作
                "present_required": List[str],  # 存在的动作
                "optional": List[str]           # 未在配置中定义的动作
            }
        """
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skins")
        skin_path = os.path.join(base_path, skin_name)

        if not os.path.isdir(skin_path):
            return {
                "valid": False,
                "missing_required": [],
                "present_required": [],
                "optional": [],
                "error": "皮肤目录不存在"
            }

        # 加载 config.json（必须存在）
        config_path = os.path.join(skin_path, "config.json")
        if not os.path.exists(config_path):
            return {
                "valid": False,
                "missing_required": [],
                "present_required": [],
                "optional": [],
                "error": "缺少 config.json 配置文件"
            }

        config = {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            return {
                "valid": False,
                "missing_required": [],
                "present_required": [],
                "optional": [],
                "error": f"配置文件加载失败: {e}"
            }

        # 从配置中获取需要验证的动作列表
        moving = config.get("moving_actions", [])
        state = config.get("state_actions", [])
        passive = config.get("passive_actions", [])
        required_actions = set(moving + state + passive)

        # 扫描所有动作子目录，验证是否有帧图片
        available = set()
        for entry in os.listdir(skin_path):
            entry_path = os.path.join(skin_path, entry)
            if os.path.isdir(entry_path):
                # 检查是否有帧图片（直接放在动作目录下）
                frames = [f for f in os.listdir(entry_path) if f.endswith('.png') or f.endswith('.gif')]
                if frames:
                    available.add(entry)
                else:
                    # 检查是否是方向变体结构（left/right 子目录）
                    has_direction_variants = all(
                        os.path.isdir(os.path.join(entry_path, direction))
                        for direction in DIRECTION_VARIANTS
                    )
                    if has_direction_variants:
                        # 检查方向子目录是否有帧
                        for direction in DIRECTION_VARIANTS:
                            dir_path = os.path.join(entry_path, direction)
                            dir_frames = [f for f in os.listdir(dir_path) if f.endswith('.png') or f.endswith('.gif')]
                            if dir_frames:
                                available.add(entry)
                                break

        # 检查配置中定义的动作是否存在
        present_required = [anim for anim in required_actions if anim in available]
        missing_required = [anim for anim in required_actions if anim not in available]
        optional = sorted([anim for anim in available if anim not in required_actions])

        return {
            "valid": len(missing_required) == 0,
            "missing_required": missing_required,
            "present_required": present_required,
            "optional": optional
        }

    @staticmethod
    def get_skin_info(skin_name: str) -> Dict[str, any]:
        """获取皮肤的详细信息"""
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skins")
        skin_path = os.path.join(base_path, skin_name)

        if not os.path.isdir(skin_path):
            return {
                "name": skin_name,
                "exists": False,
                "is_protected": skin_name == DEFAULT_SKIN,
                "animations": {}
            }

        # 加载 config.json
        config_path = os.path.join(skin_path, "config.json")
        configured_actions = set()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    moving = config.get("moving_actions", [])
                    state = config.get("state_actions", [])
                    passive = config.get("passive_actions", [])
                    configured_actions = set(moving + state + passive)
            except:
                pass

        animations = {}
        for entry in os.listdir(skin_path):
            entry_path = os.path.join(skin_path, entry)
            if os.path.isdir(entry_path):
                frames = [f for f in os.listdir(entry_path) if f.endswith('.png') or f.endswith('.gif')]
                animations[entry] = {
                    "frame_count": len(frames),
                    "is_configured": entry in configured_actions
                }

        return {
            "name": skin_name,
            "exists": True,
            "is_protected": skin_name == DEFAULT_SKIN,
            "animations": animations
        }

    @staticmethod
    def get_skin_preview_path(skin_name: str, animation_name: str = "idle", direction: str = None) -> Optional[str]:
        """获取皮肤指定动作的第一帧预览图路径

        Args:
            skin_name: 皮肤名称
            animation_name: 动作名称（如 "eat"、"idle"）
            direction: 可选的方向（"left" 或 "right"）。如果动画有方向变体，
                      未指定时默认使用 "left"。
        """
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "skins")
        anim_path = os.path.join(base_path, skin_name, animation_name)

        if not os.path.isdir(anim_path):
            return None

        # 检查是否有方向变体子目录
        has_direction_variants = all(
            os.path.isdir(os.path.join(anim_path, d))
            for d in DIRECTION_VARIANTS
        )

        if has_direction_variants:
            # 使用方向子目录，默认 "left"
            dir_name = direction if direction in DIRECTION_VARIANTS else "left"
            anim_path = os.path.join(anim_path, dir_name)

        frame_files = sorted([
            f for f in os.listdir(anim_path)
            if f.endswith('.png') or f.endswith('.gif')
        ])

        if frame_files:
            return os.path.join(anim_path, frame_files[0])
        return None

    def get_moving_actions(self) -> List[str]:
        """获取移动类动作列表

        优先使用皮肤配置中的定义，如果没有配置则使用默认分类。
        """
        # 从配置获取
        config_moving = self._config.get("moving_actions", [])
        if config_moving:
            # 确保动作实际存在
            return [a for a in config_moving if a in self.available_animations]

        # 使用默认分类
        return list(DEFAULT_MOVING_ACTIONS & set(self.available_animations.keys()))

    def get_state_actions(self) -> List[str]:
        """获取状态类动作列表

        优先使用皮肤配置中的定义，如果没有配置则使用默认分类。
        """
        # 从配置获取
        config_state = self._config.get("state_actions", [])
        if config_state:
            # 确保动作实际存在
            return [a for a in config_state if a in self.available_animations]

        # 使用默认分类
        return list(DEFAULT_STATE_ACTIONS & set(self.available_animations.keys()))

    def get_action_descriptions(self) -> Dict[str, str]:
        """获取动作描述字典"""
        return self._config.get("action_descriptions", {})

    def get_config(self) -> Dict:
        """获取皮肤配置"""
        return self._config

    def get_interactive_actions(self) -> List[str]:
        """获取可交互动作列表（可由 LLM 决策）

        从 moving_actions + state_actions 中排除被动动作
        （fall, land, held 等由系统事件触发，不应由 LLM 决策）
        """
        passive = set(self._config.get("passive_actions", DEFAULT_PASSIVE_ACTIONS))
        available = set(self.available_animations.keys())
        return [a for a in (self.get_moving_actions() + self.get_state_actions())
                if a in available and a not in passive]