"""Plector 自改进技能 - 多角色协作完成 v2.0 升级"""
import asyncio
import json
from pathlib import Path
from typing import Any

from core.event_bus import EventBus
from core.skill_handler import SkillHandler


class SkillHandler:
    """自改进 SkillHandler"""

    def __init__(self, registry=None, mcp_client=None):
        self._bus = EventBus()
        self._running = False
        self._current_phase = None
        self.name = "self_improver"

    async def start_upgrade(
        self,
        plan_file: str = "docs/reports/upgrade_plan_v2.0_integrated.md",
        phase: str = "phase_1",
        max_iterations: int = 100
    ) -> dict:
        """
        启动 Plector 自改进流程。

        流程：
        1. Planner 读取升级方案，拆解任务
        2. Coder 执行具体代码改造（2个实例并行）
        3. Tester 验证测试通过
        4. Reviewer 审查，通过后进入下一 Phase
        """
        project_root = Path(__file__).parent.parent.parent
        plan_path = project_root / plan_file

        if not plan_path.exists():
            return {"success": False, "error": f"方案文件不存在: {plan_path}"}

        plan_content = plan_path.read_text(encoding="utf-8")

        # 发布升级启动事件
        await self._bus.publish("self_improve.upgrade.started", {
            "plan_file": str(plan_path),
            "start_phase": phase,
            "max_iterations": max_iterations
        })

        self._running = True
        self._current_phase = phase

        # 构建自改进上下文
        context = {
            "plan_content": plan_content,
            "current_phase": phase,
            "iteration": 0,
            "completed_tasks": [],
            "failed_tasks": []
        }

        # 主循环：通过 event_bus 协调多角色
        results = []
        while self._running and context["iteration"] < max_iterations:
            context["iteration"] += 1

            # 发布阶段任务分配事件
            await self._bus.publish("self_improve.task.assigned", {
                "phase": context["current_phase"],
                "iteration": context["iteration"],
                "task_id": f"{context['current_phase']}_iteration_{context['iteration']}",
                "assigned_to": "planner"
            })

            # 模拟 Planner 分析方案并分配任务
            tasks = self._extract_tasks(plan_content, context["current_phase"])

            for task in tasks:
                # 分配给 Coder
                await self._bus.publish("self_improve.task.assigned", {
                    **task,
                    "assigned_to": "coder"
                })

                # 模拟 Coder 执行（实际由 agency_orchestrator 的多角色执行）
                result = await self._coders_execute(task, project_root)
                context["completed_tasks"].append(task["task_id"])

                # Tester 验证
                test_passed = await self._tester_verify(result, project_root)
                if not test_passed:
                    context["failed_tasks"].append(task["task_id"])
                    await self._bus.publish("self_improve.test.failed", {
                        "task_id": task["task_id"],
                        "result": result
                    })

            # 进入下一迭代或完成
            if context["current_phase"] == "phase_5":
                self._running = False
                break

            # 切换 Phase
            phase_map = {
                "phase_1": "phase_2", "phase_2": "phase_3",
                "phase_3": "phase_4", "phase_4": "phase_5"
            }
            context["current_phase"] = phase_map.get(context["current_phase"], "phase_5")

            await self._bus.publish("self_improve.phase.completed", {
                "phase": context["current_phase"],
                "completed_tasks": len(context["completed_tasks"]),
                "failed_tasks": len(context["failed_tasks"])
            })

            results.append({
                "phase": context["current_phase"],
                "tasks_completed": len(context["completed_tasks"]),
                "iteration": context["iteration"]
            })

        await self._bus.publish("self_improve.upgrade.completed", {
            "total_iterations": context["iteration"],
            "completed_tasks": len(context["completed_tasks"]),
            "failed_tasks": len(context["failed_tasks"]),
            "results": results
        })

        return {
            "success": True,
            "data": {
                "iterations": context["iteration"],
                "completed": len(context["completed_tasks"]),
                "failed": len(context["failed_tasks"]),
                "phases": results
            }
        }

    async def get_status(self) -> dict:
        """查询当前升级进度"""
        return {
            "success": True,
            "data": {
                "running": self._running,
                "current_phase": self._current_phase
            }
        }

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
        # 简化的任务提取，实际由 Planner 角色执行
        task_templates = {
            "phase_1": [
                {"task_id": "P1-GSD-1", "description": "实现 context_refresher skill", "files": ["skills/context_refresher/"]},
                {"task_id": "P1-GSD-2", "description": "改造 vector_memory 加 context_saver collection", "files": ["core/vector_memory.py"]},
                {"task_id": "P1-GSD-3", "description": "实现 preserve/re_anchor 逻辑", "files": ["skills/context_refresher/implementation.py"]},
            ],
            "phase_2": [
                {"task_id": "P2-LG-1", "description": "引入 LangGraph 依赖", "files": ["requirements.txt"]},
                {"task_id": "P2-LG-2", "description": "实现 workflow_graph.py", "files": ["core/workflow_graph.py"]},
                {"task_id": "P2-LG-3", "description": "改造 skill_chain 为 conditional_chain", "files": ["skills/conditional_chain/"]},
            ],
        }
        return task_templates.get(phase, [])

    async def _coders_execute(self, task: dict, project_root: Path) -> dict:
        """模拟 Coder 执行（实际由 agency_orchestrator 多角色执行）"""
        await asyncio.sleep(0.1)  # 模拟 LLM 思考时间
        return {
            "task_id": task["task_id"],
            "status": "completed",
            "files_changed": task.get("files", [])
        }

    async def _tester_verify(self, result: dict, project_root: Path) -> bool:
        """模拟 Tester 验证"""
        await asyncio.sleep(0.05)
        return result.get("status") == "completed"
