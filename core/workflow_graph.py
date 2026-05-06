# mypy: ignore-errors
"""
LangGraph 工作流引擎
===================
基于 LangGraph 的图状工作流执行器

特性:
- DAG 定义的并行执行
- 条件分支
- 循环迭代
- 断点恢复
- 状态持久化

使用方式:
    # 方式1: YAML 定义
    engine = WorkflowEngine(config)
    result = await engine.run_from_yaml("workflow.yaml", inputs={...})

    # 方式2: 代码定义
    from langgraph.graph import StateGraph
    graph = StateGraph(WorkflowState)
    graph.add_node("skill1", skill1_handler)
    graph.add_node("skill2", skill2_handler)
    graph.add_edge("skill1", "skill2", condition=lambda s: s["result"] == "ok")
    compiled = graph.compile()
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .skill_handler import SkillHandler
from .skill_registry import SkillRegistry

try:
    from langgraph.graph import END, StateGraph
except ImportError:
    StateGraph = None
    END = None

logger = logging.getLogger(__name__)


class WorkflowState(dict):
    """工作流状态"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setdefault("inputs", {})
        self.setdefault("outputs", {})
        self.setdefault("current_step", "")
        self.setdefault("history", [])
        self.setdefault("error", None)
        self.setdefault("done", False)

    def add_history(self, step: str, result: Any):
        """添加历史记录"""
        self["history"].append(
            {
                "step": step,
                "result": result,
            }
        )


class WorkflowEngine:
    """
    工作流引擎

    支持:
    - YAML 加载
    - 代码定义
    - 断点恢复
    - 事件驱动
    """

    def __init__(self, config: dict, skill_handler: SkillHandler = None):
        self._config = config
        if skill_handler is not None:
            self._skill_handler = skill_handler
        else:
            registry = SkillRegistry()
            registry.scan()
            self._skill_handler = SkillHandler(registry)
        self._graphs: dict[str, Any] = {}

    async def run_from_yaml(self, yaml_path: str, inputs: dict) -> dict:
        """
        从 YAML 文件运行工作流

        Args:
            yaml_path: YAML 文件路径
            inputs: 输入变量

        Returns:
            {"success": bool, "result": dict, "error": str}
        """
        try:
            import yaml

            with open(yaml_path, encoding="utf-8") as f:
                workflow_def = yaml.safe_load(f)

            return await self.run(workflow_def, inputs)

        except Exception as e:
            logger.exception(f"加载工作流失败: {yaml_path}")
            return {"success": False, "result": {}, "error": str(e)}

    async def run(self, workflow_def: dict, inputs: dict) -> dict:
        """
        运行工作流

        Args:
            workflow_def: 工作流定义
            inputs: 输入变量

        Returns:
            {"success": bool, "result": dict, "error": str}
        """
        try:
            # 构建状态
            state = WorkflowState(inputs=inputs)

            # 构建图
            graph = self._build_graph(workflow_def)
            if not graph:
                return {"success": False, "result": {}, "error": "图构建失败"}

            # 编译并执行
            compiled = graph.compile()
            result = await compiled.ainvoke(state)

            return {
                "success": not result.get("error"),
                "result": result.get("outputs", {}),
                "history": result.get("history", []),
            }

        except Exception as e:
            logger.exception("工作流执行失败")
            return {"success": False, "result": {}, "error": str(e)}

    def _build_graph(self, workflow_def: dict) -> StateGraph | None:
        """根据定义构建图"""
        if StateGraph is None:
            return None  # langgraph not installed, skip gracefully
        graph = StateGraph(WorkflowState)

        # 添加节点
        steps = workflow_def.get("steps", [])
        for step in steps:
            name = step.get("name")
            skill = step.get("skill")
            if skill:
                handler = self._create_skill_handler(skill, step)
                graph.add_node(name, handler)
            else:
                graph.add_node(name, lambda s: s)

        # 添加边
        for step in steps:
            name = step.get("name")
            next_step = step.get("next")

            if isinstance(next_step, str):
                if next_step == "END":
                    graph.add_edge(name, END)
                else:
                    graph.add_edge(name, next_step)

            elif isinstance(next_step, dict):
                # 条件分支
                conditions = next_step.get("conditions", {})
                for cond_name, cond_next in conditions.items():
                    cond_fn = self._create_condition(cond_name, cond_next)
                    graph.add_conditional_edges(name, cond_fn, {k: v for k, v in conditions.items()})

        # 设置入口
        entry = workflow_def.get("entry", steps[0]["name"] if steps else "")
        graph.set_entry_point(entry)

        return graph

    def _create_skill_handler(self, skill_name: str, step_def: dict):
        """创建技能处理器"""

        async def handler(state: WorkflowState) -> WorkflowState:
            state["current_step"] = skill_name

            try:
                method = step_def.get("method", "execute")
                result = await self._skill_handler.execute(
                    skill_name,
                    method,
                    {
                        **state["inputs"],
                        **step_def.get("params", {}),
                    },
                )

                state.add_history(skill_name, result)
                state["outputs"][skill_name] = result

            except Exception as e:
                logger.exception(f"技能执行失败: {skill_name}")
                state["error"] = str(e)

            return state

        return handler

    def _create_condition(self, cond_name: str, next_step: str):
        """创建条件函数"""

        def condition(state: WorkflowState) -> str:
            outputs = state.get("outputs", {})
            last_output = outputs.get(state["current_step"], {})

            if cond_name == "success":
                return next_step if last_output.get("success") else "END"
            elif cond_name == "failure":
                return next_step if not last_output.get("success") else "END"
            elif cond_name == "has_data":
                return next_step if last_output.get("data") else "END"

            return next_step

        return condition

    # ========== 断点恢复 ==========

    async def resume(self, checkpoint_path: str, inputs: dict) -> dict:
        """
        从断点恢复执行

        Args:
            checkpoint_path: 检查点文件路径
            inputs: 额外的输入变量

        Returns:
            {"success": bool, "result": dict, "error": str}
        """
        try:
            with open(checkpoint_path, encoding="utf-8") as f:
                checkpoint = json.load(f)

            state = WorkflowState(**checkpoint["state"])
            state["inputs"].update(inputs)

            # 继续执行
            graph = self._build_graph(checkpoint["workflow"])
            compiled = graph.compile()
            result = await compiled.ainvoke(state)

            return {
                "success": not result.get("error"),
                "result": result.get("outputs", {}),
            }

        except Exception as e:
            logger.exception("断点恢复失败")
            return {"success": False, "result": {}, "error": str(e)}

    async def save_checkpoint(self, state: WorkflowState, workflow_def: dict, path: str):
        """保存检查点"""
        checkpoint = {
            "state": dict(state),
            "workflow": workflow_def,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
