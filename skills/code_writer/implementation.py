#!/usr/bin/env python3
"""
代码编写技能 - 写入、读取、修改代码文件

功能：
    1. 将代码写入指定文件
    2. 读取文件内容
    3. 修改文件中的指定文本

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import logging
from pathlib import Path
from typing import Any

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """代码编写技能处理器"""

    def __init__(self):
        self.name = "code_writer"

    async def write_code(self, filepath: str, code: str) -> dict[str, Any]:
        """
        将代码写入指定文件

        参数:
            filepath: 文件路径
            code: 代码内容

        返回:
            {"success": bool, "data": {"filepath": str, "lines": int}, "error": str or None}
        """
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(code)

            lines = len(code.splitlines())

            bus = get_event_bus()
            await bus.publish(
                "code.written",
                {
                    "filepath": str(path),
                    "lines": lines,
                },
                source="code_writer",
            )

            return {
                "success": True,
                "data": {"filepath": str(path), "lines": lines},
                "error": None,
            }
        except Exception as e:
            logger.error(f"写入代码失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def read_code(self, filepath: str) -> dict[str, Any]:
        """
        读取指定文件的代码内容

        参数:
            filepath: 文件路径

        返回:
            {"success": bool, "data": {"filepath": str, "code": str, "lines": int}, "error": str or None}
        """
        try:
            path = Path(filepath)
            if not path.exists():
                return {"success": False, "data": None, "error": f"文件不存在: {filepath}"}

            code = path.read_text(encoding="utf-8")
            lines = len(code.splitlines())

            bus = get_event_bus()
            await bus.publish(
                "code.read",
                {
                    "filepath": str(path),
                    "lines": lines,
                },
                source="code_writer",
            )

            return {
                "success": True,
                "data": {"filepath": str(path), "code": code, "lines": lines},
                "error": None,
            }
        except Exception as e:
            logger.error(f"读取代码失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def modify_code(self, filepath: str, old_text: str, new_text: str) -> dict[str, Any]:
        """
        修改指定文件中的代码

        参数:
            filepath: 文件路径
            old_text: 要替换的原文
            new_text: 替换后的新内容

        返回:
            {"success": bool, "data": {"filepath": str, "replacements": int}, "error": str or None}
        """
        try:
            path = Path(filepath)
            if not path.exists():
                return {"success": False, "data": None, "error": f"文件不存在: {filepath}"}

            content = path.read_text(encoding="utf-8")
            if old_text not in content:
                return {"success": False, "data": None, "error": "未找到要替换的文本"}

            new_content = content.replace(old_text, new_text)
            replacements = content.count(old_text)
            path.write_text(new_content, encoding="utf-8")

            bus = get_event_bus()
            await bus.publish(
                "code.modified",
                {
                    "filepath": str(path),
                    "replacements": replacements,
                },
                source="code_writer",
            )

            return {
                "success": True,
                "data": {"filepath": str(path), "replacements": replacements},
                "error": None,
            }
        except Exception as e:
            logger.error(f"修改代码失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}
