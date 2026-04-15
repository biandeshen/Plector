import asyncio
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
        self.mcp_client = MCPClient(self.config)
        self.tool_registry = ToolRegistry()
        self.event_bus = get_event_bus()
        self.context_builder = ContextBuilder(self.skill_registry)
        self.skill_handler = SkillHandler(self.skill_registry, mcp_client=self.mcp_client)
        self.closure_engine = ClosureEngine(self.skill_handler)
        self.max_iterations = self.config.get("llm", {}).get("max_iterations", 10)
        self.llm = LLMClient(self.config.get("llm", {}))
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
            from core.vector_memory import VectorMemory

            memory_parts = []
            vm = VectorMemory()

            # 语义搜索相关偏好
            pref_results = await vm.search(
                query=session_id,
                collection="preferences",
                n_results=20,
            )
            if pref_results:
                memory_parts.append("## 用户偏好")
                for r in pref_results:
                    memory_parts.append(f"- {r['text']}")

            # 语义搜索当前会话的相关对话
            conv_results = await vm.search(
                query="最近的对话内容",
                collection="conversations",
                n_results=5,
                session_id=session_id,
            )
            if conv_results:
                memory_parts.append("")
                memory_parts.append("## 最近对话")
                for r in conv_results:
                    content = r["text"]
                    if len(content) > 100:
                        content = content[:100] + "..."
                    memory_parts.append(f"- {r['metadata'].get('role', 'unknown')}: {content}")

            return "\n".join(memory_parts) if memory_parts else ""

        except Exception as e:
            logger.warning(f"加载记忆失败（降级为空）: {e}")
            return ""

    def _save_conversation_sync(self, session_id: str, role: str, content: str):
        """同步保存对话记录"""
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

    async def _save_conversation(self, session_id: str, role: str, content: str):
        """保存对话记录（静默，失败不影响主流程）"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_conversation_sync, session_id, role, content)

    async def run(self, user_input: str, session_id: str = None) -> str:
        """执行 Agent 循环"""
        if session_id is None:
            session_id = "default"

        # 处理图片识别请求
        from core.image_handler import (
            get_available_backends,
            get_best_backend,
            get_image_help,
            parse_image_command,
            validate_image_path,
        )

        parsed = parse_image_command(user_input)
        if parsed:
            prompt = parsed["prompt"]
            image_path = parsed["image_path"]

            # 特殊命令：帮助
            if image_path in ["help", "帮助", "?"]:
                return get_image_help()

            # 特殊命令：列出后端
            if image_path in ["list", "列表", "后端"]:
                backends = get_available_backends()
                if not backends:
                    return "没有可用的图片识别后端"
                lines = ["可用的图片识别后端："]
                for b in backends:
                    lines.append(f"  - {b['name']} ({b['type']}, 优先级: {b['priority']})")
                return "\n".join(lines)

            # 验证图片路径
            is_valid, error_msg = validate_image_path(image_path)
            if not is_valid:
                return error_msg

            # 获取最佳后端
            backend = get_best_backend()
            if not backend:
                return "没有可用的图片识别后端，请先配置 MCP Server 或 Skill"

            # 调用后端
            try:
                if backend["type"] == "mcp":
                    result = await self.skill_handler.execute(
                        backend["server"],
                        backend["tool"],
                        {"prompt": prompt, "image_source": image_path},
                    )
                elif backend["type"] == "skill":
                    result = await self.skill_handler.execute(
                        backend["skill"],
                        backend["tool"],
                        {"prompt": prompt, "image_source": image_path},
                    )
                else:
                    return f"未知的后端类型: {backend['type']}"

                if result.get("success"):
                    data = result.get("result", {}).get("data", "")
                    return data
                else:
                    error = result.get("error", "未知错误")
                    return f"图片识别失败: {error}"

            except Exception as e:
                return f"图片识别出错: {e!s}"

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

    async def cleanup(self):
        """清理资源，防止 asyncio 子进程警告"""
        try:
            await self.mcp_client.close_all()
        except Exception as e:
            logger.warning(f"清理 MCP Client 失败: {e}")
