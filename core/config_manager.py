# core/config_manager.py
import json
import os
from typing import Dict, List, Tuple, Any


class ConfigManager:
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".deskpet", "data")
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "config.json")
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        if not os.path.exists(self.config_path):
            default_config = {
                "position": {"x": 100, "y": 100},
                "stats": {"hunger": 100, "mood": 100, "energy": 100, "age": 0},
                "custom_resources": {},
                "web_shortcuts": [],
                "llm_config": {
                    "provider": "custom",
                    "model": "InstructModelQwen3",
                    "api_key": "",
                    "base_url": "",
                    "bubble_base_url": "",
                    "bubble_api_key": "",
                    "bubble_model": ""
                },
                "action_mapping": {
                    "left_click": "wave",
                    "double_click": "jump",
                    "right_click": "menu"
                }
            }
            self._save_config(default_config)

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_config(self, config: Dict[str, Any]):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def save_position(self, x: int, y: int):
        config = self._load_config()
        config["position"] = {"x": x, "y": y}
        self._save_config(config)

    def load_position(self) -> Tuple[int, int]:
        config = self._load_config()
        pos = config.get("position", {"x": 100, "y": 100})
        return pos["x"], pos["y"]

    def save_stats(self, stats: Dict[str, int]):
        config = self._load_config()
        config["stats"] = stats
        self._save_config(config)

    def load_stats(self) -> Dict[str, int]:
        config = self._load_config()
        return config.get("stats", {"hunger": 100, "mood": 100, "energy": 100, "age": 0})

    def save_llm_config(self, llm_config: Dict[str, Any]):
        config = self._load_config()
        config["llm_config"] = llm_config
        self._save_config(config)

    def load_llm_config(self) -> Dict[str, Any]:
        config = self._load_config()
        return config.get("llm_config", {
            "provider": "openai",
            "model": "",
            "api_key": "",
            "base_url": "",
            "bubble_base_url": "",
            "bubble_api_key": "",
            "bubble_model": ""
        })

    def save_web_shortcuts(self, shortcuts: List[Dict]):
        config = self._load_config()
        config["web_shortcuts"] = shortcuts
        self._save_config(config)

    def load_web_shortcuts(self) -> List[Dict]:
        config = self._load_config()
        return config.get("web_shortcuts", [])

    def get_action_mapping(self) -> Dict[str, str]:
        config = self._load_config()
        return config.get("action_mapping", {})

    def set_action_mapping(self, mapping: Dict[str, str]):
        config = self._load_config()
        config["action_mapping"] = mapping
        self._save_config(config)

    def save_action_speeds(self, speeds: dict):
        """保存动作速度配置（移动速度）"""
        config = self._load_config()
        config["action_speeds"] = speeds
        self._save_config(config)

    def load_action_speeds(self) -> dict:
        """加载动作速度配置（移动速度）"""
        config = self._load_config()
        return config.get("action_speeds", {})

    def save_action_frame_speeds(self, speeds: dict):
        """保存动作帧率配置（动画播放速度）"""
        config = self._load_config()
        config["action_frame_speeds"] = speeds
        self._save_config(config)

    def load_action_frame_speeds(self) -> dict:
        """加载动作帧率配置（动画播放速度）"""
        config = self._load_config()
        return config.get("action_frame_speeds", {})

    def save_pet_size(self, width: int, height: int):
        """保存宠物大小"""
        config = self._load_config()
        config["pet_size"] = {"width": width, "height": height}
        self._save_config(config)

    def load_pet_size(self) -> Tuple[int, int]:
        """加载宠物大小，默认 64x64"""
        config = self._load_config()
        size = config.get("pet_size", {"width": 64, "height": 64})
        return size["width"], size["height"]

    def get_current_skin(self) -> str:
        """获取当前皮肤名称"""
        config = self._load_config()
        return config.get("current_skin", "default")

    def set_current_skin(self, skin_name: str):
        """设置当前皮肤名称"""
        config = self._load_config()
        config["current_skin"] = skin_name
        self._save_config(config)

    def save_work_records(self, records: dict):
        """保存工时记录"""
        records_path = os.path.join(self.config_dir, "work_records.json")
        with open(records_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    def load_work_records(self) -> dict:
        """加载工时记录"""
        records_path = os.path.join(self.config_dir, "work_records.json")
        if not os.path.exists(records_path):
            return {}
        try:
            with open(records_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def get_autostart(self) -> bool:
        """检查是否已设置开机自启动"""
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, "DeskPet")
                winreg.CloseKey(key)
                return bool(value)
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except WindowsError:
            return False

    def set_autostart(self, enabled: bool):
        """启用或禁用开机自启动"""
        import winreg
        import sys
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        )
        try:
            if enabled:
                exe_path = sys.executable
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
                command = f'"{exe_path}" "{script_path}"'
                winreg.SetValueEx(key, "DeskPet", 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, "DeskPet")
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)