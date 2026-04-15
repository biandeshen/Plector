#!/usr/bin/env python3
"""
auto_developer 技能实现（L2 — 一键开发封装）

调用 agency_orchestrator (L1) 的 MCP 工具，提供高层一键开发体验。
内部流程：develop → run_workflow(auto_develop.yaml) → 读取结果

Author: Plector
Version: 1.0.0
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)

SKILL_DIR = Path(__file__).parent
PROJECT_DIR = SKILL_DIR.parent.parent
AO_OUTPUT_DIR = PROJECT_DIR / "ao-output"
DEFAULT_WORKFLOW = PROJECT_DIR / "workflows" / "auto_develop.yaml"
MCP_SERVER = "agency-orchestrator"


class SkillHandler:
    """auto_developer 技能处理器（L2 — 一键开发封装）"""

    def __init__(self):
        self.name = "auto_developer"

    async def develop(
        self,
        requirement: str,
        project_dir: str = ".",
        provider: str = "claude-code",
    ) -> dict[str, Any]:
        """一键开发：运行 auto_develop.yaml 工作流"""
        if not DEFAULT_WORKFLOW.exists():
            return {
                "success": False,
                "data": None,
                "error": f"默认工作流不存在: {DEFAULT_WORKFLOW}",
            }

        await self._publish_event("auto_develop.started", {"requirement": requirement[:50]})

        return {
            "_mcp_call": MCP_SERVER,
            "tool": "run_workflow",
            "args": {
                "path": str(DEFAULT_WORKFLOW),
                "inputs": {
                    "requirement": requirement,
                    "project_dir": project_dir,
                },
                "provider": provider,
            },
        }

    async def compose(
        self,
        description: str,
        provider: str = "claude-code",
    ) -> dict[str, Any]:
        """生成工作流 YAML"""
        return {
            "_mcp_call": MCP_SERVER,
            "tool": "compose_workflow",
            "args": {"description": description, "provider": provider},
        }

    async def run(
        self,
        workflow: str,
        inputs: dict | None = None,
        provider: str = "claude-code",
    ) -> dict[str, Any]:
        """运行指定的工作流"""
        return {
            "_mcp_call": MCP_SERVER,
            "tool": "run_workflow",
            "args": {
                "path": workflow,
                "inputs": inputs or {},
                "provider": provider,
            },
        }

    async def plan(self, workflow: str) -> dict[str, Any]:
        """查看 DAG 执行计划"""
        return {
            "_mcp_call": MCP_SERVER,
            "tool": "plan_workflow",
            "args": {"path": workflow},
        }

    async def list_roles(self, category: str | None = None) -> dict[str, Any]:
        """列出角色（代理 L1）"""
        from skills.agency_orchestrator.implementation import SkillHandler as L1

        handler = L1()
        return await handler.list_roles(category)

    async def list_workflows(self) -> dict[str, Any]:
        """列出工作流模板（代理 L1）"""
        from skills.agency_orchestrator.implementation import SkillHandler as L1

        handler = L1()
        return await handler.list_workflows()

    async def read_latest_summary(self) -> dict[str, Any]:
        """读取最新的 ao-output 摘要"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._read_latest_summary_sync)

    @staticmethod
    def _read_latest_summary_sync() -> dict[str, Any]:
        """同步：读取最新 ao-output"""
        if not AO_OUTPUT_DIR.exists():
            return {"success": False, "data": None, "error": "ao-output 目录不存在"}

        dirs = sorted(
            [d for d in AO_OUTPUT_DIR.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        if not dirs:
            return {"success": False, "data": None, "error": "没有执行结果"}

        summary_file = dirs[0] / "summary.md"
        if summary_file.exists():
            content = summary_file.read_text(encoding="utf-8")
            return {"success": True, "data": {"summary": content}, "error": None}

        return {"success": False, "data": None, "error": "summary.md 不存在"}

    @staticmethod
    async def _publish_event(event_type: str, data: dict) -> None:
        """发布 CloudEvents 格式事件"""
        try:
            bus = get_event_bus()
            await bus.publish(event_type, data, source="auto_developer")
        except Exception:
            logger.debug(f"事件发布失败: {event_type}")
