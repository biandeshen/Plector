#!/usr/bin/env python3
"""
文件操作技能 - 列表、复制、移动、删除、读取文件

功能：
    1. 列出目录下的文件
    2. 复制文件
    3. 移动文件
    4. 删除文件
    5. 读取文件内容

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)

# 安全限制：禁止操作的目录
FORBIDDEN_PATHS = ["/", "C:\\", "/etc", "/usr", "/bin", "/sbin"]


class SkillHandler:
    """文件操作技能处理器"""

    def __init__(self):
        self.name = "file_utils"

    def _scan_directory_sync(self, dir_path: Path, pattern: str) -> dict[str, Any]:
        """同步扫描目录"""
        files = []
        dirs = []
        for item in sorted(dir_path.glob(pattern)):
            if item.is_file():
                files.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "size": item.stat().st_size,
                    }
                )
            elif item.is_dir():
                dirs.append(
                    {
                        "name": item.name,
                        "path": str(item),
                    }
                )
        return {"files": files, "dirs": dirs, "path": str(dir_path)}

    async def list_files(self, path=None, pattern=None) -> dict[str, Any]:
        """
        列出目录下的文件

        参数:
            path: 目录路径
            pattern: 文件匹配模式

        返回:
            {"success": bool, "data": {"files": [...], "dirs": [...]}, "error": str or None}
        """
        # 处理 null 值（OpenAI strict 模式兼容）
        if path is None:
            path = "."
        if pattern is None:
            pattern = "*"

        try:
            dir_path = Path(path)
            self._check_safe_path(dir_path)
            if not dir_path.exists():
                return {"success": False, "data": None, "error": f"目录不存在: {path}"}
            if not dir_path.is_dir():
                return {"success": False, "data": None, "error": f"不是目录: {path}"}

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._scan_directory_sync, dir_path, pattern)

            return {
                "success": True,
                "data": result,
                "error": None,
            }
        except Exception as e:
            logger.error(f"列出文件失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _copy_file_sync(self, source: str, destination: str):
        """同步复制文件"""
        src = Path(source)
        dst = Path(destination)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    async def copy_file(self, source: str, destination: str) -> dict[str, Any]:
        """
        复制文件

        参数:
            source: 源文件路径
            destination: 目标文件路径

        返回:
            {"success": bool, "data": {"source": str, "destination": str}, "error": str or None}
        """
        try:
            src = Path(source)
            dst = Path(destination)

            if not src.exists():
                return {"success": False, "data": None, "error": f"源文件不存在: {source}"}

            self._check_safe_path(src)
            self._check_safe_path(dst)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._copy_file_sync, source, destination)

            bus = get_event_bus()
            await bus.publish("file.copied", {"source": str(src), "destination": str(dst)}, source="file_utils")

            return {
                "success": True,
                "data": {"source": str(src), "destination": str(dst)},
                "error": None,
            }
        except Exception as e:
            logger.error(f"复制文件失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _move_file_sync(self, source: str, destination: str):
        """同步移动文件"""
        src = Path(source)
        dst = Path(destination)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

    async def move_file(self, source: str, destination: str) -> dict[str, Any]:
        """
        移动文件

        参数:
            source: 源文件路径
            destination: 目标文件路径

        返回:
            {"success": bool, "data": {"source": str, "destination": str}, "error": str or None}
        """
        try:
            src = Path(source)
            dst = Path(destination)

            if not src.exists():
                return {"success": False, "data": None, "error": f"源文件不存在: {source}"}

            self._check_safe_path(src)
            self._check_safe_path(dst)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._move_file_sync, source, destination)

            bus = get_event_bus()
            await bus.publish("file.moved", {"source": str(src), "destination": str(dst)}, source="file_utils")

            return {
                "success": True,
                "data": {"source": str(src), "destination": str(dst)},
                "error": None,
            }
        except Exception as e:
            logger.error(f"移动文件失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _delete_file_sync(self, filepath: str):
        """同步删除文件"""
        path = Path(filepath)
        path.unlink()

    async def delete_file(self, filepath: str) -> dict[str, Any]:
        """
        删除文件

        参数:
            filepath: 文件路径

        返回:
            {"success": bool, "data": {"filepath": str}, "error": str or None}
        """
        try:
            path = Path(filepath)

            if not path.exists():
                return {"success": False, "data": None, "error": f"文件不存在: {filepath}"}

            self._check_safe_path(path)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._delete_file_sync, filepath)

            bus = get_event_bus()
            await bus.publish("file.deleted", {"filepath": str(path)}, source="file_utils")

            return {
                "success": True,
                "data": {"filepath": str(path)},
                "error": None,
            }
        except Exception as e:
            logger.error(f"删除文件失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _read_file_sync(self, filepath: str, max_lines: int) -> tuple[str, str, int]:
        """同步读取文件"""
        path = Path(filepath)
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        if len(lines) > max_lines:
            content = "\n".join(lines[:max_lines])
            content += f"\n... (共 {len(lines)} 行，已截断到前 {max_lines} 行)"
        return str(path), content, len(lines)

    async def read_file(self, filepath: str, max_lines=None) -> dict[str, Any]:
        """
        读取文件内容

        参数:
            filepath: 文件路径
            max_lines: 最大行数

        返回:
            {"success": bool, "data": {"filepath": str, "content": str, "lines": int}, "error": str or None}
        """
        # 处理 null 值（OpenAI strict 模式兼容）
        if max_lines is None:
            max_lines = 100

        try:
            path = Path(filepath)
            self._check_safe_path(path)

            if not path.exists():
                return {"success": False, "data": None, "error": f"文件不存在: {filepath}"}

            loop = asyncio.get_event_loop()
            path_str, content, total_lines = await loop.run_in_executor(None, self._read_file_sync, filepath, max_lines)

            return {
                "success": True,
                "data": {"filepath": path_str, "content": content, "lines": total_lines},
                "error": None,
            }
        except Exception as e:
            logger.error(f"读取文件失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _check_safe_path(self, path: Path):
        """检查路径是否安全"""
        resolved = str(path.resolve())
        for forbidden in FORBIDDEN_PATHS:
            if resolved == forbidden or resolved.startswith(forbidden + os.sep):
                raise PermissionError(f"禁止操作受保护路径: {resolved}")
