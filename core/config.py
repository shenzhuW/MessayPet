"""核心配置文件 - LLM 配置"""
from __future__ import annotations
import os
import json
from dataclasses import dataclass, field
from typing import Literal, Optional

def _get_config_dir() -> str:
    """获取配置目录"""
    return os.path.join(os.path.expanduser("~"), ".deskpet", "data")

def _load_llm_config_from_file() -> dict:
    """从配置文件加载 LLM 配置"""
    config_path = os.path.join(_get_config_dir(), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("llm_config", {})
        except:
            pass
    return {}

# ============ LLM 配置 ============

def _get_default(field_name: str, env_var: str, default: str) -> str:
    """获取默认值：优先从配置文件，其次环境变量，最后默认值"""
    file_config = _load_llm_config_from_file()
    if field_name in file_config and file_config[field_name]:
        return file_config[field_name]
    return os.environ.get(env_var, default)

@dataclass
class LLMConfig:
    """LLM 客户端配置"""
    provider: Literal["openai", "anthropic", "custom"] = "custom"
    model: str = field(default_factory=lambda: _get_default("model", "ANTHROPIC_MODEL", ""))
    api_key: str = field(default_factory=lambda: _get_default("api_key", "ANTHROPIC_AUTH_TOKEN", ""))
    base_url: str = field(default_factory=lambda: _get_default("base_url", "ANTHROPIC_BASE_URL", ""))
    system_prompt: str = "你是一只可爱的像素桌面宠物。请用活泼的话语回复。"
    max_history: int = 20
    temperature: float = 0.8
    max_tokens: int = 9064

    # Bubble 显示专用配置
    bubble_base_url: str = field(default_factory=lambda: _get_default("bubble_base_url", "LLM_BASE_URL", ""))
    bubble_api_key: str = field(default_factory=lambda: _get_default("bubble_api_key", "LLM_API_KEY", ""))
    bubble_model: str = field(default_factory=lambda: _get_default("bubble_model", "LLM_MODEL", ""))


def get_llm_config() -> LLMConfig:
    """工厂函数：创建 LLMConfig"""
    return LLMConfig()