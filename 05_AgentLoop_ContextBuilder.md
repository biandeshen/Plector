---
tags: [Plector, 核心模块, 实现]
type: feature
created: 2026-04-08
---

# 变更指令：AgentLoop 集成 ContextBuilder

> 执行前确认：核心模块 10 步 + 后续三步已完成。

---

## 变更内容

1. 修改 `core/agent_loop.py`，注入 system prompt
2. 创建 `config/profiles/AGENTS.md`
3. 创建 `config/profiles/SOUL.md`
4. 创建 `config/profiles/USER.md`

---

## 第一步：修改 `core/agent_loop.py`

**改动点**：

- 添加 `from .context_builder import ContextBuilder`
- `__init__` 中创建 `self.context_builder`
- `run()` 中构建 system prompt，注入 messages

**完整文件**：

```python
import asyncio
import json
import ollama
from .skill_registry import SkillRegistry
from .skill_handler import SkillHandler
from .function_calling import ToolRegistry
from .event_bus import get_event_bus
from .context_builder import ContextBuilder


class AgentLoop:
    """自主决策循环，实现 ReAct 模式"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.skill_registry = SkillRegistry()
        self.skill_registry.scan()
        self.skill_handler = SkillHandler(self.skill_registry)
        self.tool_registry = ToolRegistry()
        self.event_bus = get_event_bus()
        self.context_builder = ContextBuilder(self.skill_registry)
        self.max_iterations = self.config.get("max_iterations", 10)
        self.model = self.config.get("model", "qwen3:4b")
        self._register_skills_as_tools()

    def _register_skills_as_tools(self):
        """将每个技能注册为工具"""
        for skill_name, skill_info in self.skill_registry.skills.items():
            for method_name, method_info in skill_info["meta"].get("methods", {}).items():
                tool_name = f"{skill_name}.{method_name}"
                self.tool_registry.register(
                    name=tool_name,
                    description=method_info.get("description", ""),
                    parameters=method_info.get("params", {}),
                    handler=self._create_skill_handler(skill_name, method_name)
                )

    def _create_skill_handler(self, skill_name, method_name):
        """创建技能调用闭包"""
        async def handler(**kwargs):
            return await self.skill_handler.execute(skill_name, method_name, kwargs)
        return handler

    async def run(self, user_input: str, session_id: str = None) -> str:
        """执行 Agent 循环"""
        system_prompt = self.context_builder.build_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        for _ in range(self.max_iterations):
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=self.model,
                    messages=messages,
                    tools=self.tool_registry.get_tool_schemas()
                )
            )
            if not response.get("message", {}).get("tool_calls"):
                return response["message"]["content"]

            for tool_call in response["message"]["tool_calls"]:
                result = await self.tool_registry.execute(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": json.dumps(result)
                })

        return "达到最大迭代次数"
```

---

## 第二步：创建 `config/profiles/AGENTS.md`

```markdown
# AGENTS.md

## 项目简介
Plector - 事件驱动的 AI Agent 引擎，支持技能治理和闭环自愈。

## 快速导航
| 你想做什么 | 去哪里看 |
|-----------|----------|
| 了解系统架构 | docs/specs/Design_Plector_v1.2.md |
| 了解编码规范 | docs/standards/Code_Standard_Plector.md |
| 了解技能开发 | docs/standards/Skill_Development_Plector.md |
| 了解闭环配置 | config/closed_loops.yaml |

## 硬性规则
1. core/ 不依赖 skills/ 和 tools/
2. 技能数量 ≤ 15
3. 函数不超过 50 行
4. 返回值格式: {"success", "data", "error"}
```

---

## 第三步：创建 `config/profiles/SOUL.md`

```markdown
# SOUL.md

## Plector 的性格
- 务实、简洁、高效
- 先验证再优化
- 出错时返回结构化错误，不抛异常
- 拒绝过度工程化
```

---

## 第四步：创建 `config/profiles/USER.md`

```markdown
# USER.md

## 用户偏好
- 中文交流
- 代码风格遵循 Code Standard
- 提交后自动 push
```

---

## 验证

```bash
# 1. 语法检查
python -m py_compile core/agent_loop.py

# 2. 导入测试
python -c "
from core.agent_loop import AgentLoop
a = AgentLoop()
prompt = a.context_builder.build_system_prompt()
print(prompt[:200])
"

# 3. 预期输出包含
# - AGENTS.md 内容
# - SOUL.md 内容
# - USER.md 内容
# - ## 可用技能
# - health_monitor
# - error_knowledge

# 4. CLI 测试
python channels/cli.py --query "你有哪些技能？"
# 预期：列出 health_monitor 和 error_knowledge
```

---

## 提交

```bash
git add core/agent_loop.py config/profiles/
git commit -m "feat(core): AgentLoop 集成 ContextBuilder，注入 system prompt"
git push
```

---

## 变更摘要

| 文件 | 操作 | 说明 |
|------|------|------|
| core/agent_loop.py | 修改 | 添加 ContextBuilder 集成 + system prompt 注入 |
| config/profiles/AGENTS.md | 新建 | 索引地图，50 行以内 |
| config/profiles/SOUL.md | 新建 | Agent 性格定义 |
| config/profiles/USER.md | 新建 | 用户偏好 |
```

---

**直接执行。从第一步开始，每步验证后再继续。**