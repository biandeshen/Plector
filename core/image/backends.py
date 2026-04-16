"""
图片处理后端管理
"""

import logging
import threading
from typing import Optional

from .config import IMAGE_BACKENDS

logger = logging.getLogger(__name__)

# 全局锁
_backend_lock = threading.Lock()

# 后端注册表
_registered_backends: dict[str, dict] = dict(IMAGE_BACKENDS)


def get_available_backends() -> list[dict]:
    """获取所有可用的后端列表"""
    with _backend_lock:
        return [
            backend for backend in _registered_backends.values()
            if backend.get("enabled", True)
        ]


def get_best_backend() -> Optional[dict]:
    """获取优先级最高的后端"""
    backends = get_available_backends()
    if not backends:
        return None
    return max(backends, key=lambda x: x.get("priority", 0))


def register_backend(name: str, config: dict) -> bool:
    """
    注册新的图片处理后端

    配置格式:
        {
            "type": "mcp" | "skill" | "api",
            "server": "server_name",      # MCP server 名称
            "skill": "skill_name",         # 或技能名称
            "tool": "tool_name",           # 工具名
            "priority": 10,                # 优先级
            "enabled": True,
        }
    """
    with _backend_lock:
        if name in _registered_backends:
            logger.warning(f"后端 {name} 已存在，将被覆盖")
        _registered_backends[name] = config
        return True


def unregister_backend(name: str) -> bool:
    """注销后端"""
    with _backend_lock:
        if name in _registered_backends:
            del _registered_backends[name]
            return True
        return False


def enable_backend(name: str) -> bool:
    """启用后端"""
    with _backend_lock:
        if name in _registered_backends:
            _registered_backends[name]["enabled"] = True
            return True
        return False


def disable_backend(name: str) -> bool:
    """禁用后端"""
    with _backend_lock:
        if name in _registered_backends:
            _registered_backends[name]["enabled"] = False
            return True
        return False


def get_backend(name: str) -> Optional[dict]:
    """获取指定后端的配置"""
    with _backend_lock:
        return _registered_backends.get(name)
