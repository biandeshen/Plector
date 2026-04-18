import asyncio
import json
import logging
import os
import re
import sqlite3
import time

from .closure_engine import ClosureEngine
from .config_loader import load_config
from .context_builder import ContextBuilder
from .event_bus_v2 import get_event_bus_v2 as get_event_bus
from .function_calling import ToolRegistry
from .llm_client_v2 import LLMClientV2 as LLMClient
from .metrics import get_metrics_collector, Timer
from .mcp_client import MCPClient
from .skill_handler import SkillHandler
from .skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


def filter_think_tags(content: str) -> str:
    """
    过滤 `﹏﹟` 标签及其内容

    处理三种格式：
        ﹏﹟...﹟
        ﹏﹟
        ﹟
    """
    if not content:
        return content

    # 移除 `﹏﹟` 标签及其内容
    content = re.sub(r"﹏﹟.*?﹟", "", content, flags=re.DOTALL)

    # 移除残留的开启标签
    content = re.sub(r"﹏﹟.*", "", content, flags=re.DOTALL)

    # 移除残留的关闭标签
    content = re.sub(r"﹟", "", content)

    # 清理多余空行
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


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
            await self.mcp_client.connect_all()
            all_tools = await self.mcp_client.list_all_tools()
            self.mcp_client.register_to_tool_registry(self.tool_registry, all_tools)
            self._mcp_initialized = True
            logger.info(f"MCP Client 初始化完成，注册了 {sum(len(tools) for tools in all_tools.values())} 个远程工具")
        except Exception as e:
            logger.warning(f"MCP Client 初始化失败: {type(e).__name__}: {e}")
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
            from core.vector_memory_v2 import VectorMemoryV2 as VectorMemory

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
        db_path = os.environ.get("PECTOR_DB_PATH", "data/plector.db")
        try:
            conn = sqlite3.connect(db_path)
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

    async def cleanup(self):
        """清理资源，防止 asyncio 子进程警告"""
        try:
            await self.mcp_client.close_all()
        except Exception as e:
            logger.warning(f"清理 MCP Client 失败: {e}")

    async def _handle_image_command(self, user_input: str):
        """处理图片识别命令，返回 (done, content) 元组"""
        from core.image_handler import (
            get_available_backends,
            get_best_backend,
            get_image_help,
            parse_image_command,
            validate_image_path,
        )

        parsed = parse_image_command(user_input)
        if not parsed:
            return None

        prompt = parsed["prompt"]
        image_path = parsed["image_path"]

        if image_path in ["help", "帮助", "?"]:
            return True, get_image_help()
        if image_path in ["list", "列表", "后端"]:
            backends = get_available_backends()
            if not backends:
                return True, "没有可用的图片识别后端"
            content = "\n".join([f"  - {b['name']} ({b['type']})" for b in backends])
            return True, content

        is_valid, error_msg = validate_image_path(image_path)
        if not is_valid:
            return True, error_msg

        backend = get_best_backend()
        if not backend:
            return True, "没有可用的图片识别后端"

        try:
            if backend["type"] == "mcp":
                result = await self.skill_handler.execute(
                    backend["server"], backend["tool"], {"prompt": prompt, "image_source": image_path}
                )
            else:
                result = await self.skill_handler.execute(
                    backend["skill"], backend["tool"], {"prompt": prompt, "image_source": image_path}
                )
            content = (
                result.get("result", {}).get("data", "")
                if result.get("success")
                else f"图片识别失败: {result.get('error', '未知错误')}"
            )
            return True, content
        except Exception as e:
            return True, f"图片识别出错: {e}"

    async def _build_messages(self, user_input: str, session_id: str) -> list[dict]:
        """构建初始消息列表"""
        memory_context = await self._load_memory(session_id)
        system_prompt = self.context_builder.build_system_prompt()
        if memory_context:
            system_prompt += "\n\n" + memory_context
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]

    async def _collect_stream_events(self, messages: list[dict]):
        """收集流式事件，返回 (full_response, tool_calls_buffer)"""
        full_response = ""
        tool_calls_buffer = []

        async for event in self.llm.stream_chat(messages, self.tool_registry.get_tool_schemas()):
            etype = event.get("type")

            if etype == "content":
                filtered = filter_think_tags(event["content"])
                full_response += filtered
                if filtered:
                    yield {"type": "chunk", "content": filtered}

            elif etype == "tool_call":
                if event["tool_call"] not in tool_calls_buffer:
                    tool_calls_buffer.append(event["tool_call"])

            elif etype == "done":
                if event.get("tool_calls"):
                    for tc in event["tool_calls"]:
                        if tc not in tool_calls_buffer:
                            tool_calls_buffer.append(tc)
                break

        yield {"type": "done", "full_response": full_response, "tool_calls_buffer": tool_calls_buffer}

    async def _execute_tool_calls(self, tool_calls_buffer: list, messages: list):
        """执行工具调用并返回结果"""
        for tc in tool_calls_buffer:
            tool_name = tc["function"]["name"]
            metrics = get_metrics_collector()
            metrics.inc_tool_call(tool_name)
            yield {"type": "toolExecuting", "tool": tool_name}

            tool_call = {
                "id": tc.get("id", f"call_{tool_calls_buffer.index(tc)}"),
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                },
            }
            result = await self.tool_registry.execute(tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result),
                }
            )
            yield {
                "type": "toolDone",
                "tool": tc["function"]["name"],
                "result": str(result)[:100],
            }

    async def _handle_no_tool_calls(self, full_response: str, session_id: str):
        """处理没有 tool_calls 的情况"""
        filtered_response = filter_think_tags(full_response)
        await self._save_conversation(session_id, "assistant", filtered_response)
        return filtered_response

    def _build_assistant_message(self, full_response: str, tool_calls_buffer: list) -> dict:
        """构建 assistant 消息"""
        return {
            "role": "assistant",
            "content": full_response,
            "tool_calls": [
                {
                    "id": tc.get("id", f"call_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                }
                for i, tc in enumerate(tool_calls_buffer)
            ],
        }

    async def run_streaming(self, user_input: str, session_id: str = None):
        """流式执行 Agent 循环，yield 事件"""
        metrics = get_metrics_collector()
        start_time = time.perf_counter()

        if session_id is None:
            session_id = "default"

        result = await self._handle_image_command(user_input)
        if result:
            yield {"type": "done", "content": result[1]}
            return

        await self._ensure_mcp_initialized()
        await self._save_conversation(session_id, "user", user_input)

        messages = await self._build_messages(user_input, session_id)

        for _ in range(self.max_iterations):
            metrics.inc_iteration()

            collected = None
            async for event in self._collect_stream_events(messages):
                if event.get("type") == "done":
                    collected = event
                    break
                yield event

            if collected is None:
                continue

            full_response = collected["full_response"]
            tool_calls_buffer = collected["tool_calls_buffer"]

            if not tool_calls_buffer:
                filtered_response = await self._handle_no_tool_calls(full_response, session_id)
                yield {"type": "done", "content": filtered_response}
                return

            messages.append(self._build_assistant_message(full_response, tool_calls_buffer))
            await self._finalize_iteration(session_id, full_response, tool_calls_buffer, messages)

        yield {"type": "done", "content": "达到最大迭代次数"}

        duration = time.perf_counter() - start_time
        metrics.record_agent_response_time(duration)

    async def _finalize_iteration(self, session_id: str, full_response: str, tool_calls_buffer: list, messages: list):
        """保存助手响应并执行工具调用"""
        if full_response:
            filtered_response = filter_think_tags(full_response)
            await self._save_conversation(session_id, "assistant", filtered_response)

        yield {"type": "tool_call_start", "count": len(tool_calls_buffer)}

        async for event in self._execute_tool_calls(tool_calls_buffer, messages):
            yield event
