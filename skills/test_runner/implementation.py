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
from typing import Any, ClassVar

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """测试运行技能处理器"""

    def __init__(self):
        self.name = "test_runner"

    async def run_tests(self, path=None) -> dict[str, Any]:
        """
        运行 pytest 测试

        参数:
            path: 测试路径，默认 tests/

        返回:
            {"success": bool, "data": {"passed": int, "failed": int, "output": str}, "error": str or None}
        """
        # 处理 null 值（OpenAI strict 模式兼容）
        if path is None:
            path = "tests/"

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: self._run_pytest(path, timeout=60))

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

    # 允许的安全命令白名单
    ALLOWED_COMMANDS: ClassVar[set[str]] = {"pytest", "python", "pip"}

    async def run_command(self, command: str, timeout=None) -> dict[str, Any]:
        """
        运行预批准的命令（仅限白名单）

        参数:
            command: 要执行的命令（仅限 pytest/python/pip）
            timeout: 超时时间（秒）

        返回:
            {"success": bool, "data": {"command": str, "output": str, "returncode": int}, "error": str or None}
        """
        # 处理 null 值（OpenAI strict 模式兼容）
        if timeout is None:
            timeout = 30

        # 安全检查：仅允许白名单命令
        cmd_base = command.strip().split()[0] if command.strip() else ""
        if cmd_base not in self.ALLOWED_COMMANDS:
            return {
                "success": False,
                "data": None,
                "error": f"命令不被允许: {cmd_base}（仅限: {', '.join(self.ALLOWED_COMMANDS)}）",
            }

        try:
            loop = asyncio.get_running_loop()
            args = command.strip().split()
            result = await loop.run_in_executor(None, lambda: self._run_safe(args, timeout))

            return {
                "success": result["returncode"] == 0,
                "data": {"command": command, "output": result["output"], "returncode": result["returncode"]},
                "error": None if result["returncode"] == 0 else f"命令返回码: {result['returncode']}",
            }
        except Exception as e:
            logger.error(f"运行命令失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _run_pytest(self, path: str, timeout: int) -> dict[str, Any]:
        """安全运行 pytest（参数列表化，禁止 shell 注入）"""
        import subprocess

        try:
            result = subprocess.run(
                ["pytest", path, "-v", "--tb=short"],
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return {"output": result.stdout + result.stderr, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"output": f"命令超时（{timeout}秒）", "returncode": -1}

    def _run_safe(self, args: list[str], timeout: int) -> dict[str, Any]:
        """安全执行命令（参数列表化，禁止 shell 注入）"""
        import subprocess

        try:
            result = subprocess.run(
                args,
                shell=False,
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
