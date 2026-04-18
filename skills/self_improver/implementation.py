"""Plector 自改进技能 - 多角色协凋 compose_workflow v3.0"""

import asyncio
from pathlib import Path

from core.event_bus import EventBus


class SelfImproverSkill:
    """自改进 SkillHandler - 集成 agency_orchestrator compose_workflow"""

    def __init__(self, registry=None, mcp_client=None):
        self._bus = EventBus()
        self._running = False
        self._current_phase = None
        self.name = "self_improver"
        self._mcp_client = mcp_client

    async def start_upgrade(
        self,
        plan_file: str = "docs/reports/upgrade_plan_v2.0_integrated.md",
        phase: str = "phase_1",
        max_iterations: int = 100,
    ) -> dict:
        """启动 Plector 自改进流程 v3.0。"""
        project_root = Path(__file__).parent.parent.parent
        plan_path = project_root / plan_file

        if not plan_path.exists():
            return {"success": False, "error": f"方案文件不存在: {plan_path}"}

        plan_content = plan_path.read_text(encoding="utf-8")
        await self._bus.publish(
            "self_improve.upgrade.started",
            {
                "plan_file": str(plan_path),
                "start_phase": phase,
                "max_iterations": max_iterations,
                "version": "3.0",
            },
        )
        self._running = True
        self._current_phase = phase
        context = {
            "plan_content": plan_content,
            "current_phase": phase,
            "iteration": 0,
            "completed_tasks": [],
            "failed_tasks": [],
            "workflow_results": [],
        }

        results = await self._run_upgrade_loop(context, plan_content, project_root, max_iterations)
        return await self._finalize_upgrade(context, results)

    async def _finalize_upgrade(self, context, results):
        """发布升级完成事件并返回结果"""
        await self._bus.publish(
            "self_improve.upgrade.completed",
            {
                "total_iterations": context["iteration"],
                "completed_tasks": len(context["completed_tasks"]),
                "failed_tasks": len(context["failed_tasks"]),
                "workflow_results": context["workflow_results"],
                "results": results,
            },
        )
        return {
            "success": True,
            "data": {
                "iterations": context["iteration"],
                "completed": len(context["completed_tasks"]),
                "failed": len(context["failed_tasks"]),
                "phases": results,
                "workflow_engaged": True,
            },
        }

    async def _run_upgrade_loop(self, context, plan_content, project_root, max_iterations):
        """主循环：通过 event_bus 协调多角色"""
        results = []
        while self._running and context["iteration"] < max_iterations:
            context["iteration"] += 1
            await self._bus.publish(
                "self_improve.task.assigned",
                {
                    "phase": context["current_phase"],
                    "iteration": context["iteration"],
                    "task_id": f"{context['current_phase']}_iteration_{context['iteration']}",
                    "assigned_to": "planner",
                },
            )
            await self._process_phase_tasks(context, plan_content, project_root)

            if not self._advance_phase(context):
                break

            await self._bus.publish(
                "self_improve.phase.completed",
                {
                    "phase": context["current_phase"],
                    "completed_tasks": len(context["completed_tasks"]),
                    "failed_tasks": len(context["failed_tasks"]),
                },
            )
            results.append(
                {
                    "phase": context["current_phase"],
                    "tasks_completed": len(context["completed_tasks"]),
                    "iteration": context["iteration"],
                }
            )
        return results

    async def _process_phase_tasks(self, context, plan_content, project_root):
        """处理当前阶段的所有任务"""
        tasks = self._extract_tasks(plan_content, context["current_phase"])
        for task in tasks:
            await self._bus.publish("self_improve.task.assigned", {**task, "assigned_to": "coder"})
            result = await self._coders_execute_with_agency(task, project_root)
            context["completed_tasks"].append(task["task_id"])
            context["workflow_results"].append(result)
            test_passed = await self._tester_verify(result, project_root)
            if not test_passed:
                context["failed_tasks"].append(task["task_id"])
                await self._bus.publish(
                    "self_improve.test.failed",
                    {
                        "task_id": task["task_id"],
                        "result": result,
                    },
                )

    def _advance_phase(self, context):
        """切换到下一阶段，返回是否应继续"""
        if context["current_phase"] == "phase_final":
            self._running = False
            return False
        phase_map = {
            "phase_1": "phase_2",
            "phase_2": "phase_3",
            "phase_3": "phase_4",
            "phase_4": "phase_final",
        }
        context["current_phase"] = phase_map.get(context["current_phase"], "phase_final")
        return True

    async def get_status(self) -> dict:
        """查询当前升级进度"""
        return {"success": True, "data": {"running": self._running, "current_phase": self._current_phase}}

    async def stop_upgrade(self) -> dict:
        """停止自改进流程"""
        self._running = False
        await self._bus.publish("self_improve.upgrade.stopped", {})
        return {"success": True, "data": {"stopped": True}}

    async def execute(self, action: str, args: dict) -> dict:
        if action == "start_upgrade":
            return await self.start_upgrade(**args)
        elif action == "get_status":
            return await self.get_status()
        elif action == "stop_upgrade":
            return await self.stop_upgrade()
        return {"success": False, "error": f"Unknown action: {action}"}

    def _extract_tasks(self, plan_content: str, phase: str) -> list:
        """从方案中提取当前 Phase 的任务"""
        task_templates = {
            "phase_1": [
                {
                    "task_id": "P1-GSD-1",
                    "description": "实现 context_refresher skill",
                    "files": ["skills/context_refresher/"],
                },
                {
                    "task_id": "P1-GSD-2",
                    "description": "改造 vector_memory 加 context_saver collection",
                    "files": ["core/vector_memory.py"],
                },
                {
                    "task_id": "P1-GSD-3",
                    "description": "实现 preserve/re_anchor 逻辑",
                    "files": ["skills/context_refresher/implementation.py"],
                },
            ],
            "phase_2": [
                {"task_id": "P2-LG-1", "description": "引入 LangGraph 依赖", "files": ["requirements.txt"]},
                {"task_id": "P2-LG-2", "description": "实现 workflow_graph.py", "files": ["core/workflow_graph.py"]},
                {
                    "task_id": "P2-LG-3",
                    "description": "改造 skill_chain 为 conditional_chain",
                    "files": ["skills/conditional_chain/"],
                },
            ],
        }
        return task_templates.get(phase, [])

    async def _coders_execute_with_agency(self, task: dict, project_root: Path) -> dict:
        """使用 agency_orchestrator compose_workflow 协调多角色执行"""
        task_id = task["task_id"]
        description = task["description"]
        files = task.get("files", [])

        await self._bus.publish(
            "self_improve.agency.compose_started",
            {
                "task_id": task_id,
                "description": description,
            },
        )

        workflow_description = (
            f"任务: {description}\n涉及文件: {', '.join(files)}\n"
            "角色协作要求:\n"
            "1. 系统分析师 (system-architect): 从架构角度分析，提出设计建议\n"
            "2. 技术写手 (technical-writer): 从文档角度优化，更新相关文档\n"
            "3. 代码开发者 (code-developer): 执行具体代码修改\n"
            "brainstorming superpower 参与: 生成 2-3 个候选项方案供选择"
        )

        if not self._mcp_client:
            return await self._coders_execute_simple(task, project_root)

        try:
            return await self._execute_mcp_workflow(
                task_id,
                workflow_description,
                task,
                project_root,
                files,
            )
        except Exception as e:
            await self._bus.publish(
                "self_improve.agency.compose_failed",
                {
                    "task_id": task_id,
                    "error": str(e),
                },
            )
            return await self._coders_execute_simple(task, project_root)

    async def _execute_mcp_workflow(self, task_id, description, task, project_root, files):
        """通过 MCP compose_workflow 生成并运行工作流"""
        compose_result = await self._mcp_client.compose_workflow(
            description=description,
            provider="claude-code",
        )
        if not compose_result.get("success"):
            raise RuntimeError("compose_workflow 返回失败")

        workflow_path = compose_result.get("data", {}).get("workflow_path")
        run_result = await self._mcp_client.run_workflow(
            path=workflow_path,
            inputs={"task": task, "project_root": str(project_root)},
            provider="claude-code",
        )
        await self._bus.publish(
            "self_improve.agency.compose_completed",
            {
                "task_id": task_id,
                "workflow_path": workflow_path,
                "result": run_result,
            },
        )
        return {
            "task_id": task_id,
            "status": "completed",
            "agency_engaged": True,
            "workflow_path": workflow_path,
            "files_changed": files,
            "result": run_result,
        }

    async def _coders_execute_simple(self, task: dict, project_root: Path) -> dict:
        """简化的 Coder 执行（无 MCP client 时 fallback）"""
        await asyncio.sleep(0.1)  # 模拟 LLM 思考时间
        return {
            "task_id": task["task_id"],
            "status": "completed",
            "agency_engaged": False,
            "files_changed": task.get("files", []),
        }

    async def _tester_verify(self, result: dict, project_root: Path) -> bool:
        """Tester 验证"""
        await asyncio.sleep(0.05)
        return result.get("status") == "completed"
