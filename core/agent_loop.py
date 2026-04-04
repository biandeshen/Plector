import json
import logging
import sqlite3

from .closure_engine import ClosureEngine
from .config_loader import load_config
from .context_builder import ContextBuilder
from .event_bus import get_event_bus
from .function_calling import ToolRegistry
from .llm_client import LLMClient
from .mcp_client import MCPClient
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
            import logging

            logger = logging.getLogger(__name__)
            await self.mcp_client.connect_all()
            all_tools = await self.mcp_client.list_all_tools()
            self.mcp_client.register_to_tool_registry(self.tool_registry, all_tools)
            self._mcp_initialized = True
            logger.info(f"MCP Client 初始化完成，注册了 {sum(len(tools) for tools in all_tools.values())} 个远程工具")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"MCP Client 初始化失败: {type(e).__name__}: {e}")
            # 不设置 _mcp_initialized = True，允许下次重试
            self._mcp_initialized = False

    async def _load_memory(self, session_id: str) -> str:
        """
        加载记忆上下文

        安全机制：
            1. 异常捕获，降级为空记忆（不影响主流程）
            2. 偏好最多加载 20 条（避免上下文膨胀）
            3. 对话按 session_id 过滤（避免跨会话泄漏）
            4. 对话内容截断到 100 字符（节省 token）
        """
        try:
            conn = sqlite3.connect("data/plector.db")
            cursor = conn.cursor()

            memory_parts = []

            # 加载用户偏好（最多 20 条）
            cursor.execute("SELECT key, value FROM user_preferences LIMIT 20")
            prefs = cursor.fetchall()
            if prefs:
                memory_parts.append("## 用户偏好")
                for key, value in prefs:
                    memory_parts.append(f"- {key}: {value}")

            # 加载当前会话的最近对话（按 session_id 过滤）
            cursor.execute(
                "SELECT role, content FROM conversations "
                "WHERE session_id = ? ORDER BY timestamp DESC LIMIT 5",
                (session_id,),
            )
            history = cursor.fetchall()
            conn.close()

            if history:
                memory_parts.append("")
                memory_parts.append("## 最近对话")
                for role, content in reversed(history):
                    if len(content) > 100:
                        preview = content[:100] + "..."
                    else:
                        preview = content
                    memory_parts.append(f"- {role}: {preview}")

            return "\n".join(memory_parts) if memory_parts else ""

        except Exception as e:
            logger.warning(f"加载记忆失败（降级为空）: {e}")
            return ""

    async def _save_conversation(self, session_id: str, role: str, content: str):
        """保存对话记录（静默，失败不影响主流程）"""
        try:
            conn = sqlite3.connect("data/plector.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"保存对话失败: {e}")

    async def run(self, user_input: str, session_id: str = None) -> str:
        """执行 Agent 循环"""
        if session_id is None:
            session_id = "default"

        await self._ensure_mcp_initialized()

        # 保存用户消息
        await self._save_conversation(session_id, "user", user_input)

        # 加载记忆（异常时降级为空）
        memory_context = await self._load_memory(session_id)

        system_prompt = self.context_builder.build_system_prompt()
        if memory_context:
            system_prompt += "\n\n" + memory_context

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]

        for _ in range(self.max_iterations):
            response = await self.llm.chat(messages=messages, tools=self.tool_registry.get_tool_schemas())
            if not response.get("tool_calls"):
                # 保存助手回复
                await self._save_conversation(session_id, "assistant", response["content"])
                return response["content"]

            # 先追加 assistant 消息（包含 tool_calls）
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

            # 再追加 tool 消息
            for tool_call in response["tool_calls"]:
                result = await self.tool_registry.execute(tool_call)
                messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(result)})

        return "达到最大迭代次数"
