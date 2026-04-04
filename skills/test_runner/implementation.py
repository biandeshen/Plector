#!/usr/bin/env python3
"""
测试运行技能 - 运行测试并返回结果

功能：
    1. 运行 pytest 测试
    2. 运行任意 shell 命令
    3. 发布测试事件

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import asyncio
import logging
from typing import Any

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """测试运行技能处理器"""

    def __init__(self):
        self.name = "test_runner"

    async def run_tests(self, path: str = "tests/") -> dict[str, Any]:
        """
        运行 pytest 测试

        参数:
            path: 测试路径，默认 tests/

        返回:
            {"success": bool, "data": {"passed": int, "failed": int, "output": str}, "error": str or None}
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self._run_command(f"pytest {path} -v --tb=short", timeout=60)
            )

            passed = result["output"].count(" PASSED")
            failed = result["output"].count(" FAILED")
            total = passed + failed
            success = failed == 0 and total > 0

            await self._publish_test_result(success, path, passed, failed, total, result["output"])

            return {
                "success": success,
                "data": {"passed": passed, "failed": failed, "total": total, "output": result["output"]},
                "error": None if success else f"{failed} 个测试失败",
            }
        except Exception as e:
            logger.error(f"运行测试失败: {e}", exc_info=True)
            await self._publish_test_error(path, str(e))
            return {"success": False, "data": None, "error": str(e)}

    async def run_command(self, command: str, timeout: int = 30) -> dict[str, Any]:
        """
        运行任意 shell 命令

        参数:
            command: 要执行的命令
            timeout: 超时时间（秒）

        返回:
            {"success": bool, "data": {"command": str, "output": str, "returncode": int}, "error": str or None}
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._run_command(command, timeout))

            return {
                "success": result["returncode"] == 0,
                "data": {"command": command, "output": result["output"], "returncode": result["returncode"]},
                "error": None if result["returncode"] == 0 else f"命令返回码: {result['returncode']}",
            }
        except Exception as e:
            logger.error(f"运行命令失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _run_command(self, command: str, timeout: int) -> dict[str, Any]:
        """同步执行命令（在线程池中运行）"""
        import subprocess

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return {"output": result.stdout + result.stderr, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"output": f"命令超时（{timeout}秒）", "returncode": -1}

    async def _publish_test_result(self, success: bool, path: str, passed: int, failed: int, total: int, output: str):
        """发布测试结果事件"""
        bus = get_event_bus()
        if success:
            await bus.publish("test.passed", {"path": path, "passed": passed, "total": total}, source="test_runner")
        else:
            await bus.publish(
                "test.failed",
                {"path": path, "passed": passed, "failed": failed, "total": total, "output": output},
                source="test_runner",
            )

    async def _publish_test_error(self, path: str, error: str):
        """发布测试错误事件"""
        bus = get_event_bus()
        await bus.publish("test.failed", {"path": path, "error": error}, source="test_runner")
