#!/usr/bin/env python3
"""
Agency Orchestrator 技能实现（L1 — MCP Server 直接封装）

提供 7 个工具：
- run_workflow: 执行 YAML 工作流（MCP 代理）
- validate_workflow: 校验工作流（MCP 代理）
- list_workflows: 列出工作流模板（本地只读）
- plan_workflow: 显示 DAG 执行计划（MCP 代理）
- compose_workflow: 自然语言生成工作流（MCP 代理）
- list_roles: 列出 AI 角色（本地只读）
- get_role: 获取角色定义（本地只读）

本地只读工具直接读文件，AI 执行工具走 MCP 代理（_mcp_call 标记）。

Author: Plector
Version: 1.1.0
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)

SKILL_DIR = Path(__file__).parent
ROLES_DIR = SKILL_DIR.parent.parent / "external-skills" / "roles"
WORKFLOWS_DIR = (
    SKILL_DIR.parent.parent
    / "servers"
    / "agency-orchestrator"
    / "workflows"
)
MCP_SERVER = "agency-orchestrator"


class SkillHandler:
    """Agency Orchestrator 技能处理器（L1）"""

    def __init__(self):
        self.name = "agency_orchestrator"

    # ─── 本地只读工具 ───

    async def list_roles(self, category: str | None = None) -> dict[str, Any]:
        """列出 AI 角色，直接读 external-skills/roles/"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._list_roles_sync, category)

    def _list_roles_sync(self, category: str | None) -> dict[str, Any]:
        """同步：扫描角色目录"""
        if not ROLES_DIR.exists():
            return {"success": False, "data": None, "error": f"角色目录不存在: {ROLES_DIR}"}

        result = {}
        for cat_dir in sorted(ROLES_DIR.iterdir()):
            if not cat_dir.is_dir():
                continue
            if category and cat_dir.name != category:
                continue
            result[cat_dir.name] = self._scan_role_files(cat_dir)

        return {
            "success": True,
            "data": {
                "categories": list(result.keys()),
                "roles": result,
                "total": sum(len(v) for v in result.values()),
            },
            "error": None,
        }

    @staticmethod
    def _scan_role_files(cat_dir: Path) -> list[str]:
        """扫描分类目录下的角色文件名"""
        roles = []
        for f in sorted(cat_dir.iterdir()):
            if f.suffix == ".md":
                roles.append(f.stem.replace(f"{cat_dir.name}-", ""))
        return roles

    async def get_role(self, category: str, name: str) -> dict[str, Any]:
        """获取角色定义，直接读 .md 文件"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_role_sync, category, name)

    def _get_role_sync(self, category: str, name: str) -> dict[str, Any]:
        """同步：读取角色文件"""
        role_file = self._find_role_file(category, name)
        if not role_file:
            return {"success": False, "data": None, "error": f"角色不存在: {category}/{name}"}

        content = role_file.read_text(encoding="utf-8")
        fm_name, fm_desc = self._parse_frontmatter(content)

        return {
            "success": True,
            "data": {
                "category": category,
                "name": fm_name or name,
                "description": fm_desc,
                "content": content,
            },
            "error": None,
        }

    @staticmethod
    def _find_role_file(category: str, name: str) -> Path | None:
        """查找角色文件，尝试带前缀和不带前缀"""
        candidates = [
            ROLES_DIR / category / f"{name}.md",
            ROLES_DIR / category / f"{category}-{name}.md",
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[str, str]:
        """解析 YAML frontmatter，返回 (name, description)"""
        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            return ("", "")
        try:
            import yaml
            fm = yaml.safe_load(fm_match.group(1))
            return (fm.get("name", ""), fm.get("description", ""))
        except Exception:
            return ("", "")

    async def list_workflows(self) -> dict[str, Any]:
        """列出工作流模板，直接读 workflows/ 目录"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._list_workflows_sync)

    def _list_workflows_sync(self) -> dict[str, Any]:
        """同步：扫描工作流目录"""
        if not WORKFLOWS_DIR.exists():
            return {"success": False, "data": None, "error": f"工作流目录不存在: {WORKFLOWS_DIR}"}

        templates = self._scan_workflow_files()
        return {
            "success": True,
            "data": {"count": len(templates), "templates": templates},
            "error": None,
        }

    @staticmethod
    def _scan_workflow_files() -> list[dict]:
        """递归扫描工作流目录"""
        import yaml as _yaml

        templates = []
        for f in sorted(WORKFLOWS_DIR.rglob("*.yaml")):
            rel = f.relative_to(WORKFLOWS_DIR)
            try:
                doc = _yaml.safe_load(f.read_text(encoding="utf-8"))
                templates.append({
                    "name": str(rel).replace("\\", "/"),
                    "desc": doc.get("description", doc.get("name", "")),
                })
            except Exception:
                templates.append({
                    "name": str(rel).replace("\\", "/"),
                    "desc": "(解析失败)",
                })
        return templates

    # ─── MCP 代理工具 ───

    async def run_workflow(
        self,
        path: str,
        inputs: dict | None = None,
        provider: str = "claude-code",
        model: str | None = None,
        resume: str | None = None,
        from_step: str | None = None,
    ) -> dict[str, Any]:
        """执行 YAML 工作流 → MCP: agency-orchestrator.run_workflow"""
        args: dict[str, Any] = {
            "path": path,
            "inputs": inputs or {},
            "provider": provider,
        }
        if model:
            args["model"] = model
        if resume:
            args["resume"] = resume
        if from_step:
            args["from_step"] = from_step

        await self._publish_event("workflow.executed", {"path": path})
        return {"_mcp_call": MCP_SERVER, "tool": "run_workflow", "args": args}

    async def validate_workflow(self, path: str) -> dict[str, Any]:
        """校验工作流 → MCP: agency-orchestrator.validate_workflow"""
        return {"_mcp_call": MCP_SERVER, "tool": "validate_workflow", "args": {"path": path}}

    async def plan_workflow(self, path: str) -> dict[str, Any]:
        """DAG 执行计划 → MCP: agency-orchestrator.plan_workflow"""
        return {"_mcp_call": MCP_SERVER, "tool": "plan_workflow", "args": {"path": path}}

    async def compose_workflow(
        self,
        description: str,
        provider: str = "claude-code",
        model: str | None = None,
    ) -> dict[str, Any]:
        """自然语言生成 YAML → MCP: agency-orchestrator.compose_workflow"""
        args: dict[str, Any] = {"description": description, "provider": provider}
        if model:
            args["model"] = model

        await self._publish_event("workflow.composed", {"description": description[:50]})
        return {"_mcp_call": MCP_SERVER, "tool": "compose_workflow", "args": args}

    # ─── 事件发布 ───

    @staticmethod
    async def _publish_event(event_type: str, data: dict) -> None:
        """发布 CloudEvents 格式事件"""
        try:
            bus = get_event_bus()
            await bus.publish(event_type, data, source="agency_orchestrator")
        except Exception:
            logger.debug(f"事件发布失败: {event_type}")
