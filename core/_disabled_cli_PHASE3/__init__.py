"""Plector CLI 模块化架构

职责分离：
- __init__.py: 导出主入口
- parser.py: 参数解析
- commands/: 命令子模块
"""

from .main import main

__all__ = ["main"]
