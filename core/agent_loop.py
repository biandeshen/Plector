import asyncio
import json
import yaml
import ollama
from .skill_registry import SkillRegistry
from .skill_handler import SkillHandler
from .function_calling import ToolRegistry
from .event_bus import get_event_bus
from .closure_engine import ClosureEngine
from .context_builder import ContextBuilder

class AgentLoop:
    def __init__(self, config_path: str = "config/config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.llm_config = self.config.get("llm", {})
        self.skill_registry = SkillRegistry()
        self.skill_registry.scan()
        self.skill_handler = SkillHandler(self.skill_registry)
        self.tool_registry = ToolRegistry()
        self.event_bus = get_event_bus()
        self.max_iterations = self.llm_config.get("max_iterations", 10)
        self.model = self.llm_config.get("model", "llama3.2")
        self._register_skills_as_tools()
        # Initialize closure engine to subscribe to events
        self.closure_engine = ClosureEngine(self.skill_handler, "config/closed_loops.yaml")
        # Initialize context builder for system prompt
        self.context_builder = ContextBuilder(self.skill_registry)

    def _register_skills_as_tools(self):
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
        async def handler(**kwargs):
            return await self.skill_handler.execute(skill_name, method_name, kwargs)
        return handler

    async def run(self, user_input: str, session_id: str = None) -> str:
        system_prompt = self.context_builder.build_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        for _ in range(self.max_iterations):
            # Ollama 目前是同步 API，用线程池执行
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
            # 执行工具调用
            for tool_call in response["message"]["tool_calls"]:
                result = await self.tool_registry.execute(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": json.dumps(result)
                })
        return "达到最大迭代次数"
