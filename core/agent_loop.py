import json
import logging

from .closure_engine import ClosureEngine
from .config_loader import load_config
from .context_builder import ContextBuilder
from .conversation_store import ConversationStore
from .event_bus import get_event_bus
from .function_calling import ToolRegistry
from .image_router import ImageRouter
from .llm_client import LLMClient
from .mcp_client import MCPClient
from .memory_loader import MemoryLoader
from .skill_handler import SkillHandler
from .skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


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
        self.mcp_client = MCPClient(self.config)
        self._mcp_initialized = False
        self.conversation_store = ConversationStore()
        self.memory_loader = MemoryLoader(self.context_builder)
        self.image_router = ImageRouter(self.skill_handler)
        self._register_skills_as_tools()

    def _register_skills_as_tools(self):
        """将每个技能的工具注册为 LLM 可调用工具（MCP 格式，使用 _ 分隔符）"""
        for skill_name, skill_info in self.skill_registry.skills.items():
            for tool_def in skill_info["meta"].get("tools", []):
                tool_name = f"{skill_name}_{tool_def['name']}"
                self.tool_registry.register(
                    name=tool_name,
                    description=tool_def.get("description", ""),
                    input_schema=tool_def.get(
                        "inputSchema",
                        {
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        },
                    ),
                    handler=self._create_skill_handler(skill_name, tool_def["name"]),
                )

    def _create_skill_handler(self, skill_name, method_name):
        async def handler(**kwargs):
            return await self.skill_handler.execute(skill_name, method_name, kwargs)

        return handler

    async def _ensure_mcp_initialized(self):
        """懒加载 MCP 工具"""
        if self._mcp_initialized:
            return
        try:
            await self.mcp_client.connect_all()
            all_tools = await self.mcp_client.list_all_tools()
            self.mcp_client.register_to_tool_registry(self.tool_registry, all_tools)
            self._mcp_initialized = True
            logger.info(f"MCP Client 初始化完成，注册了 {sum(len(tools) for tools in all_tools.values())} 个远程工具")
        except Exception as e:
            logger.warning(f"MCP Client 初始化失败: {type(e).__name__}: {e}")
            self._mcp_initialized = False

    async def run(self, user_input: str, session_id: str = None) -> str:
        """执行 Agent 循环"""
        if session_id is None:
            session_id = "default"

        # 图片识别请求
        image_result = await self.image_router.handle(user_input)
        if image_result is not None:
            return image_result

        await self._ensure_mcp_initialized()

        # 保存用户消息
        await self.conversation_store.save(session_id, "user", user_input)

        # 组装系统提示词 + 记忆
        memory_context = await self.memory_loader.load(session_id)
        system_prompt = self.memory_loader.build_system_prompt(memory_context)

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]

        return await self._run_react_loop(session_id, messages)

    async def _run_react_loop(self, session_id: str, messages: list[dict]) -> str:
        """ReAct 循环核心"""
        for _ in range(self.max_iterations):
            response = await self.llm.chat(messages=messages, tools=self.tool_registry.get_tool_schemas())
            if not response.get("tool_calls"):
                await self.conversation_store.save(session_id, "assistant", response["content"])
                return response["content"]

            messages.append(
                {
                    "role": "assistant",
                    "content": response["content"],
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                        }
                        for tc in response["tool_calls"]
                    ],
                }
            )

            for tool_call in response["tool_calls"]:
                result = await self.tool_registry.execute(tool_call)
                messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(result)})

        return "达到最大迭代次数"

    async def cleanup(self):
        """清理资源，防止 asyncio 子进程警告"""
        try:
            await self.mcp_client.close_all()
        except Exception as e:
            logger.warning(f"清理 MCP Client 失败: {e}")
