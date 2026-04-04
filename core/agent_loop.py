import asyncio
import json
from .skill_registry import SkillRegistry
from .skill_handler import SkillHandler
from .function_calling import ToolRegistry
from .event_bus import get_event_bus
from .closure_engine import ClosureEngine
from .context_builder import ContextBuilder
from .llm_client import LLMClient
from .config_loader import load_config


class AgentLoop:
    """自主决策循环，实现 ReAct 模式"""

    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.skill_registry = SkillRegistry()
        self.skill_registry.scan()
        self.skill_handler = SkillHandler(self.skill_registry)
        self.tool_registry = ToolRegistry()
        self.event_bus = get_event_bus()
        self.context_builder = ContextBuilder(self.skill_registry)
        self.closure_engine = ClosureEngine(self.skill_handler)
        self.max_iterations = self.config.get("llm", {}).get("max_iterations", 10)
        self.llm = LLMClient(self.config.get("llm", {}))
        self._register_skills_as_tools()

    def _register_skills_as_tools(self):
        """将每个技能的工具注册为 LLM 可调用工具（MCP 格式，使用 _ 分隔符）"""
        for skill_name, skill_info in self.skill_registry.skills.items():
            for tool_def in skill_info["meta"].get("tools", []):
                # 使用 _ 作为分隔符，符合 OpenAI 工具命名规范
                tool_name = f"{skill_name}_{tool_def['name']}"
                self.tool_registry.register(
                    name=tool_name,
                    description=tool_def.get("description", ""),
                    input_schema=tool_def.get("inputSchema", {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    }),
                    handler=self._create_skill_handler(skill_name, tool_def["name"])
                )

    def _create_skill_handler(self, skill_name, method_name):
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
            response = await self.llm.chat(
                messages=messages,
                tools=self.tool_registry.get_tool_schemas()
            )
            if not response.get("tool_calls"):
                return response["content"]

            # 先追加 assistant 消息（包含 tool_calls）
            messages.append({
                "role": "assistant",
                "content": response["content"],
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"]
                        }
                    }
                    for tc in response["tool_calls"]
                ]
            })

            # 再追加 tool 消息
            for tool_call in response["tool_calls"]:
                result = await self.tool_registry.execute(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result)
                })

        return "达到最大迭代次数"
