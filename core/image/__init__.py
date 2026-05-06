"""
图片处理模块 - v2.0 拆分版
==========================
支持多后端的图片识别

目录结构:
    config.py     - 常量配置
    validator.py  - 路径和URL验证
    backends.py  - 后端管理
    handler.py    - 主处理器

使用方式:
    from core.image import ImageHandler, get_best_backend

    handler = ImageHandler()
    result = await handler.analyze("path/to/image.png")
"""

from .backends import get_available_backends, get_best_backend, register_backend
from .config import (
    IMAGE_BACKENDS,
    IMAGE_COMMANDS,
    MAX_FILE_SIZE,
    SUPPORTED_FORMATS,
)
from .handler import ImageHandler
from .validator import validate_image_path, validate_image_source

__all__ = [
    # 配置
    "IMAGE_BACKENDS",
    "IMAGE_COMMANDS",
    "MAX_FILE_SIZE",
    "SUPPORTED_FORMATS",
    # 入口类
    "ImageHandler",
    # 函数
    "get_available_backends",
    "get_best_backend",
    "register_backend",
    "validate_image_path",
    "validate_image_source",
]
