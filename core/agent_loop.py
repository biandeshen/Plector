from .skill_registry import SkillRegistry
from .skill_handler import SkillHandler
from .function_calling import ToolRegistry
from .event_bus import get_event_bus

class AgentLoop:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.skill_registry = SkillRegistry()
        self.skill_registry.scan()
        self.skill_handler = SkillHandler(self.skill_registry)
        self.tool_registry = ToolRegistry()
        self.event_bus = get_event_bus()
        self.max_iterations = self.config.get("max_iterations", 10)
        self._register_skills_as_tools()

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
        # 占位：需集成真实 LLM 客户端
        print(f"AgentLoop received: {user_input}")
        # TODO: 集成 OpenAI/Anthropic 等 LLM 客户端
        return f"Echo: {user_input}"
