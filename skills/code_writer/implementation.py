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

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)

# 安全限制：禁止操作的目录
FORBIDDEN_PATHS = ["/", "C:\\", "/etc", "/usr", "/bin", "/sbin"]


class SkillHandler:
    """代码编写技能处理器"""

    def __init__(self):
        self.name = "code_writer"

    def _check_safe_path(self, path: Path):
        """检查路径是否安全"""
        resolved = str(path.resolve())
        for forbidden in FORBIDDEN_PATHS:
            if resolved == forbidden or resolved.startswith(forbidden + os.sep):
                raise PermissionError(f"禁止操作受保护路径: {resolved}")

    def _write_code_sync(self, filepath: str, code: str) -> tuple[str, int]:
        """同步写入代码"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return str(path), len(code.splitlines())

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
            p = Path(filepath)
            self._check_safe_path(p)
            loop = asyncio.get_event_loop()
            path, lines = await loop.run_in_executor(None, self._write_code_sync, filepath, code)

            bus = get_event_bus()
            await bus.publish(
                "code.written",
                {
                    "filepath": path,
                    "lines": lines,
                },
                source="code_writer",
            )

            return {
                "success": True,
                "data": {"filepath": path, "lines": lines},
                "error": None,
            }
        except Exception as e:
            logger.error(f"写入代码失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _read_code_sync(self, filepath: str) -> tuple[str, str, int]:
        """同步读取代码"""
        path = Path(filepath)
        code = path.read_text(encoding="utf-8")
        return str(path), code, len(code.splitlines())

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
            self._check_safe_path(path)
            if not path.exists():
                return {"success": False, "data": None, "error": f"文件不存在: {filepath}"}

            loop = asyncio.get_event_loop()
            path_str, code, lines = await loop.run_in_executor(None, self._read_code_sync, filepath)

            bus = get_event_bus()
            await bus.publish(
                "code.read",
                {
                    "filepath": path_str,
                    "lines": lines,
                },
                source="code_writer",
            )

            return {
                "success": True,
                "data": {"filepath": path_str, "code": code, "lines": lines},
                "error": None,
            }
        except Exception as e:
            logger.error(f"读取代码失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _modify_code_sync(self, filepath: str, old_text: str, new_text: str) -> tuple[str, int]:
        """同步修改代码"""
        path = Path(filepath)
        content = path.read_text(encoding="utf-8")
        new_content = content.replace(old_text, new_text)
        replacements = content.count(old_text)
        path.write_text(new_content, encoding="utf-8")
        return str(path), replacements

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
            self._check_safe_path(path)
            if not path.exists():
                return {"success": False, "data": None, "error": f"文件不存在: {filepath}"}

            content = path.read_text(encoding="utf-8")
            if old_text not in content:
                return {"success": False, "data": None, "error": "未找到要替换的文本"}

            loop = asyncio.get_event_loop()
            path_str, replacements = await loop.run_in_executor(
                None, self._modify_code_sync, filepath, old_text, new_text
            )

            bus = get_event_bus()
            await bus.publish(
                "code.modified",
                {
                    "filepath": path_str,
                    "replacements": replacements,
                },
                source="code_writer",
            )

            return {
                "success": True,
                "data": {"filepath": path_str, "replacements": replacements},
                "error": None,
            }
        except Exception as e:
            logger.error(f"修改代码失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}
