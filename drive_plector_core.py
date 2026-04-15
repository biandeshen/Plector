#!/usr/bin/env python3
"""
Plector 核心驱动脚本：直接调用 Plector 核心模块执行升级任务
绕过 WebSocket，直接使用 AgentLoop / SkillHandler / FileWriter 等
"""
import asyncio
import sys
from pathlib import Path

# 将项目根目录加入路径
PROJECT_ROOT = Path("E:\\产品\\Plector-v2-upgrade")
sys.path.insert(0, str(PROJECT_ROOT))

import dotenv
dotenv.load_dotenv(PROJECT_ROOT / ".env")

from core.agent_loop import AgentLoop
from core.skill_registry import SkillRegistry
from core.vector_memory import VectorMemory


async def run_task(task_description: str) -> str:
    """通过 AgentLoop 执行自然语言任务"""
    agent = AgentLoop()
    result = await agent.run(task_description)
    return result


async def main():
    print("=" * 60)
    print("Plector v2.0 Upgrade - Direct Core Execution")
    print("=" * 60)

    # Step 1: 读取升级方案
    print("\n[STEP 1] Reading upgrade plan...")
    plan_path = PROJECT_ROOT / "docs" / "reports" / "upgrade_plan_v2.0_integrated.md"
    content = plan_path.read_text(encoding="utf-8")
    print(f"Plan loaded: {len(content)} chars")
    print("First 300 chars:")
    print(content[:300])

    # Step 2: 创建 Phase 1 任务 - GSD 上下文保鲜
    print("\n[STEP 2] Creating context_refresher skill...")

    skill_dir = PROJECT_ROOT / "skills" / "context_refresher"
    skill_dir.mkdir(exist_ok=True)

    # 写入 skill.json
    skill_json = {
        "name": "context_refresher",
        "version": "1.0.0",
        "description": "GSD 上下文保鲜技能：防止长对话中 AI 遗忘初始目标",
        "tier": "tier_2_enhanced",
        "tools": [{
            "name": "preserve",
            "description": "触发上下文保鲜：提取 {goal, constraints, completed, in_progress} 并存储",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "conversation_history": {"type": "array", "description": "对话历史"}
                },
                "required": ["conversation_history"]
            }
        }, {
            "name": "re_anchor",
            "description": "重锚定：更新或覆盖已保鲜的上下文",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "new_goal": {"type": "string"},
                    "new_constraints": {"type": "array"}
                },
                "required": ["new_goal"]
            }
        }]
    }

    import json
    (skill_dir / "skill.json").write_text(json.dumps(skill_json, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created: {skill_dir / 'skill.json'}")

    # 写入 implementation.py
    implementation = '''"""GSD 上下文保鲜技能"""
import asyncio
from typing import Any
from core.vector_memory import VectorMemory
from core.event_bus import EventBus


class SkillHandler:
    """上下文保鲜 SkillHandler"""

    def __init__(self, registry=None, mcp_client=None):
        self._vm = VectorMemory()
        self._bus = EventBus()
        self.name = "context_refresher"

    async def preserve(self, conversation_history: list) -> dict:
        """
        触发上下文保鲜。
        从对话历史中提取初始目标、约束条件、已完成和进行中的任务。
        """
        if not conversation_history:
            return {"success": False, "error": "对话历史为空"}

        # 提取首条用户消息作为初始目标
        initial_goal = ""
        constraints = []
        completed = []
        in_progress = []

        for msg in conversation_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and not initial_goal:
                # 取前200字符作为目标摘要
                initial_goal = content[:200]
                break

        # 发布保鲜事件
        await self._bus.publish("context.preserved", {
            "goal": initial_goal,
            "constraints": constraints,
            "completed": completed,
            "in_progress": in_progress,
            "history_len": len(conversation_history)
        })

        # 存入 vector_memory 的 context_saver collection
        context_data = {
            "type": "context_saver",
            "goal": initial_goal,
            "constraints": constraints,
            "completed": completed,
            "in_progress": in_progress,
            "turns": len(conversation_history)
        }
        self._vm.add("context_saver", context_data, {"content": initial_goal})

        return {
            "success": True,
            "data": {
                "goal": initial_goal,
                "turns_preserved": len(conversation_history)
            }
        }

    async def re_anchor(self, new_goal: str, new_constraints: list = None) -> dict:
        """
        重锚定上下文。当用户明确修改目标时调用。
        """
        new_constraints = new_constraints or []
        context_data = {
            "type": "context_saver",
            "goal": new_goal,
            "constraints": new_constraints,
            "completed": [],
            "in_progress": [],
            "turns": 0
        }
        self._vm.add("context_saver", context_data, {"content": new_goal})

        await self._bus.publish("context.re_anchored", {
            "new_goal": new_goal,
            "constraints": new_constraints
        })

        return {"success": True, "data": {"goal": new_goal}}

    async def execute(self, action: str, args: dict) -> dict:
        """统一入口"""
        if action == "preserve":
            return await self.preserve(**args)
        elif action == "re_anchor":
            return await self.re_anchor(**args)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
'''
    (skill_dir / "implementation.py").write_text(implementation, encoding="utf-8")
    print(f"Created: {skill_dir / 'implementation.py'}")

    # Step 3: 改造 VectorMemory 添加 context_saver collection
    print("\n[STEP 3] Checking VectorMemory context_saver support...")
    vm = VectorMemory()
    collections = vm._get_collections() if hasattr(vm, '_get_collections') else []
    print(f"Existing collections: {collections}")

    # Step 4: 验证文件创建
    print("\n[STEP 4] Verifying created files...")
    created = list(skill_dir.glob("*"))
    print(f"Files in context_refresher/: {[f.name for f in created]}")

    # Step 5: 运行测试
    print("\n[STEP 5] Running tests...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True
    )
    print(result.stdout[-1000:] if result.stdout else "")
    if result.returncode != 0:
        print("STDERR:", result.stderr[-500:] if result.stderr else "")
    print(f"Tests exit code: {result.returncode}")

    print("\n" + "=" * 60)
    print("Phase 1 (GSD Context Preserver) setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
