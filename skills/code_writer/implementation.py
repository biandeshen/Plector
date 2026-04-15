#!/usr/bin/env python3
"""
代码编写技能 - 写入、读取、修改代码文件

功能：
    1. 将代码写入指定文件
    2. 读取文件内容
    3. 修改文件中的指定文本

Author: Plector
Version: 1.1.0
Created: 2026-04-04
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)

# 路径安全：允许写入的根目录（项目工作目录 + 用户主目录）
_ALLOWED_ROOTS: list[str] | None = None


def _get_allowed_roots() -> list[str]:
    """获取允许操作的根目录列表（延迟计算）"""
    global _ALLOWED_ROOTS
    if _ALLOWED_ROOTS is None:
        roots = [str(Path.cwd().resolve()), str(Path.home().resolve())]
        # 添加环境变量指定的额外根目录
        extra = os.environ.get("PECTOR_ALLOWED_ROOTS", "")
        if extra:
            roots.extend(p.strip() for p in extra.split(os.pathsep) if p.strip())
        _ALLOWED_ROOTS = roots
    return _ALLOWED_ROOTS


def _is_path_allowed(filepath: str) -> tuple[bool, str]:
    """检查路径是否在允许的目录内（防路径穿越）"""
    try:
        resolved = Path(filepath).resolve()
        for root in _get_allowed_roots():
            try:
                resolved.relative_to(root)
                return True, ""
            except ValueError:
                continue
        return False, f"路径不在允许的目录内: {filepath}（允许: {', '.join(_get_allowed_roots())}）"
    except Exception as e:
        return False, f"路径验证失败: {e}"


class SkillHandler:
    """代码编写技能处理器"""

    def __init__(self):
        self.name = "code_writer"

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
        # 路径安全检查
        path_ok, path_err = _is_path_allowed(filepath)
        if not path_ok:
            return {"success": False, "data": None, "error": path_err}

        try:
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
        # 路径安全检查
        path_ok, path_err = _is_path_allowed(filepath)
        if not path_ok:
            return {"success": False, "data": None, "error": path_err}

        try:
            path = Path(filepath)
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
        # 路径安全检查
        path_ok, path_err = _is_path_allowed(filepath)
        if not path_ok:
            return {"success": False, "data": None, "error": path_err}

        try:
            path = Path(filepath)
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
