import asyncio
import json
import logging
import logging.config
import os
import re
import sqlite3
import time

import yaml

from .closure_engine import ClosureEngine
from .config_loader import load_config
from .context_builder import ContextBuilder
from .event_bus_v2 import get_event_bus_v2 as get_event_bus
from .function_calling import ToolRegistry
from .governance import Governance
from .llm_client_v2 import LLMClientV2 as LLMClient
from .mcp_client import MCPClient
from .metrics import get_metrics_collector
from .skill_handler import SkillHandler
from .skill_registry import SkillRegistry
from .vector_memory_v2 import VectorMemoryV2

logger = logging.getLogger(__name__)


def setup_logging():
    """Load logging configuration from config/logging_config.yaml and apply PLECTOR_LOG_LEVEL override."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "logging_config.yaml")
    try:
        with open(config_path, encoding="utf-8") as f:
            log_config = yaml.safe_load(f)
    except Exception as e:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        logging.warning(f"Failed to load logging config from {config_path}: {e}")
        return

    # Apply PLECTOR_LOG_LEVEL override to root logger
    log_level = os.environ.get("PLECTOR_LOG_LEVEL", "").upper()
    if log_level:
        log_config["root"]["level"] = log_level

    # Ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    logging.config.dictConfig(log_config)


def filter_think_tags(content: str) -> str:
    """
    过滤 think 标签及其内容

    处理多种格式：
        <think>...</think> (标准格式，如 qwen3)
        <thinking>...</thinking> (XML 格式)
        ﹏﹟...﹟ (自定义分隔符，如 MiniMax)
    """
    if not content:
        return content

    # 移除完整的 <think>...</think> 标签及其内容
    content = re.sub(r"<think>[\s\S]*?</think>", "", content)
    # 移除不完整的 <think> 开标签（到字符串末尾）
    content = re.sub(r"<think>[\s\S]*$", "", content)
    # 移除孤立的 </think> 闭标签
    content = re.sub(r"</think>", "", content)

    # 移除完整的 <thinking>...</thinking> 标签及其内容
    content = re.sub(r"<thinking>[\s\S]*?</thinking>", "", content)
    # 移除不完整的 <thinking> 开标签
    content = re.sub(r"<thinking>[\s\S]*$", "", content)
    # 移除孤立的 </thinking> 闭标签
    content = re.sub(r"</thinking>", "", content)

    # 移除自定义分隔符格式 ﹏﹟...﹟
    content = re.sub(r"﹏﹟.*?﹟", "", content, flags=re.DOTALL)

    # 移除残留的自定义开启标签
    content = re.sub(r"﹏﹟.*", "", content, flags=re.DOTALL)

    # 移除残留的自定义关闭标签
    content = re.sub(r"﹟", "", content)

    # 清理多余空行
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


def _extract_tool_result_text(result: dict, max_len: int = 500) -> str:
    """
    从工具执行结果中提取核心信息，用于显示给用户。

    处理 jsonrpc 格式：
        {"jsonrpc": "2.0", "id": "...", "result": {"success": true/false, "data": ..., "error": ...}}
    """
    if not isinstance(result, dict):
        return str(result)[:max_len]

    # 处理 jsonrpc 格式
    if "jsonrpc" in result:
        inner = result.get("result", {})
        if isinstance(inner, dict):
            if not inner.get("success", True):
                # 失败情况：显示错误信息
                error = inner.get("error", "")
                return error if error else "执行失败"
            # 成功情况：提取 data 字段
            data = inner.get("data")
            if data is not None:
                text = str(data)
                return text[:max_len] + ("..." if len(text) > max_len else "")
            return "执行成功"
        return str(result)[:max_len]

    # 非 jsonrpc 格式，直接转字符串
    return str(result)[:max_len]


class AgentLoop:
    """自主决策循环，实现 ReAct 模式"""

    def __init__(self, config: dict = None):
        setup_logging()
        self.config = config or load_config()
        self.skill_registry = SkillRegistry()
        self.skill_registry.scan()
        self.mcp_client = MCPClient(self.config)
        self.tool_registry = ToolRegistry()
        self.event_bus = get_event_bus()
        self.context_builder = ContextBuilder(self.skill_registry)
        self.skill_handler = SkillHandler(self.skill_registry, mcp_client=self.mcp_client)
        self.closure_engine = ClosureEngine(self.skill_handler)
        self.governance = Governance(self.skill_registry, self.event_bus)
        self.max_iterations = self.config.get("llm", {}).get("max_iterations", 10)
        self.refresh_interval = self.config.get("context_refresher", {}).get("refresh_interval", 10)
        self.llm = LLMClient(self.config.get("llm", {}))
        self._mcp_initialized = False
        self._turn_count = 0
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
        """同步保存对话记录，返回 rowid"""
        db_path = os.environ.get("PLECTOR_DB_PATH", "data/plector.db")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            conn.commit()
            rowid = cursor.lastrowid
            conn.close()
            return rowid
        except Exception as e:
            logger.warning(f"保存对话失败: {e}")
            return None

    async def _save_conversation(self, session_id: str, role: str, content: str):
        """保存对话记录（静默，失败不影响主流程）"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_conversation_sync, session_id, role, content)

    def _save_tool_call_sync(
        self,
        session_id: str,
        message_index: int,
        tool_name: str,
        arguments: str,
        result: str,
        elapsed: float,
        thinking: str = "",
    ):
        """同步保存工具调用记录"""
        db_path = os.environ.get("PLECTOR_DB_PATH", "data/plector.db")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tool_calls (session_id, message_index, tool_name, arguments, result, elapsed, thinking) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, message_index, tool_name, arguments, result, elapsed, thinking),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"保存工具调用失败: {e}")

    async def _save_tool_call(
        self,
        session_id: str,
        message_index: int,
        tool_name: str,
        arguments: str,
        result: str,
        elapsed: float,
        thinking: str = "",
    ):
        """保存工具调用记录（静默，失败不影响主流程）"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, self._save_tool_call_sync, session_id, message_index, tool_name, arguments, result, elapsed, thinking
        )

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

        # 处理 help/list 命令
        help_result = self._image_handle_help_list(image_path, get_available_backends, get_image_help)
        if help_result is not None:
            return help_result

        # 验证图片路径和后端
        validation_result = self._image_validate(image_path, validate_image_path, get_best_backend)
        if validation_result is not None:
            return validation_result

        # 执行图片识别
        return await self._image_execute(prompt, image_path, get_best_backend)

    def _image_handle_help_list(self, image_path, get_backends_fn, get_help_fn):
        """处理 help/list 命令"""
        if image_path in ["help", "帮助", "?"]:
            return True, get_help_fn()
        if image_path in ["list", "列表", "后端"]:
            backends = get_backends_fn()
            if not backends:
                return True, "没有可用的图片识别后端"
            content = "\n".join([f"  - {b['name']} ({b['type']})" for b in backends])
            return True, content
        return None

    def _image_validate(self, image_path, validate_fn, get_backend_fn):
        """验证图片路径和后端"""
        is_valid, error_msg = validate_fn(image_path)
        if not is_valid:
            return True, error_msg
        backend = get_backend_fn()
        if not backend:
            return True, "没有可用的图片识别后端"
        return None

    async def _image_execute(self, prompt, image_path, get_backend_fn):
        """执行图片识别"""
        backend = get_backend_fn()
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

    def _upsert_tool_call(self, buffer: list, tool_call: dict, thinking: str = "") -> None:
        """查找并更新或插入工具调用记录"""
        for i, existing_tc in enumerate(buffer):
            if existing_tc.get("id") == tool_call.get("id"):
                if thinking and not buffer[i].get("thinking"):
                    buffer[i]["thinking"] = thinking
                return
        buffer.append({**tool_call, "thinking": thinking})

    def _extract_thinking_from_buffer(self, raw_buffer: str) -> str:
        """从 raw_buffer 中提取思考内容"""
        if hasattr(self.llm, "_extract_thinking"):
            return self.llm._extract_thinking(raw_buffer)
        return ""

    async def _collect_stream_events(self, messages: list[dict]):
        """收集流式事件，使用 buffer 级增量过滤解决跨 chunk 标签分割问题"""
        full_response = ""
        tool_calls_buffer = []
        raw_buffer = ""
        last_yielded_len = 0

        async for event in self.llm.stream_chat(messages, self.tool_registry.get_tool_schemas()):
            etype = event.get("type")

            if etype == "content":
                raw_buffer += event["content"]
                filtered_full = filter_think_tags(raw_buffer)
                new_content = filtered_full[last_yielded_len:]
                full_response = filtered_full
                if new_content:
                    last_yielded_len = len(filtered_full)
                    yield {"type": "chunk", "content": new_content}

            elif etype == "tool_call":
                thinking = self._extract_thinking_from_buffer(raw_buffer)
                self._upsert_tool_call(tool_calls_buffer, event["tool_call"], thinking)
                raw_buffer = ""
                last_yielded_len = 0

            elif etype == "done":
                if event.get("tool_calls"):
                    thinking = self._extract_thinking_from_buffer(raw_buffer)
                    for tc in event["tool_calls"]:
                        self._upsert_tool_call(tool_calls_buffer, tc, thinking)
                break

        yield {"type": "done", "full_response": full_response, "tool_calls_buffer": tool_calls_buffer}

    async def _execute_single_tool(self, tc: dict, messages: list, session_id: str = None, message_index: int = None):
        """执行单个工具调用，返回结果事件"""
        tool_name = tc["function"]["name"]
        tool_id = tc.get("id", "call_0")
        arguments = tc["function"].get("arguments", "")
        thinking = tc.get("thinking", "")

        tool_call = {"id": tool_id, "function": {"name": tool_name, "arguments": arguments}}
        result = await self.tool_registry.execute(tool_call)
        elapsed = time.perf_counter() - tc["_start_time"]

        # 更新技能健康分
        self._update_skill_health(tool_name, result, elapsed)

        messages.append({"role": "tool", "tool_call_id": tool_id, "content": json.dumps(result)})

        result_text = _extract_tool_result_text(result)
        clean_thinking = filter_think_tags(thinking) if thinking else ""
        if session_id is not None and message_index is not None:
            await self._save_tool_call(
                session_id, message_index, tool_name, arguments, result_text, elapsed, clean_thinking
            )
        return {
            "type": "toolDone",
            "tool": tool_name,
            "toolId": tool_id,
            "result": result_text,
            "thinking": clean_thinking,
        }

    async def _execute_tool_calls(
        self, tool_calls_buffer: list, messages: list, session_id: str = None, message_index: int = None
    ):
        """执行工具调用并返回结果"""
        for tc in tool_calls_buffer:
            tool_name = tc["function"]["name"]
            tool_id = tc.get("id", f"call_{tool_calls_buffer.index(tc)}")
            arguments = tc["function"].get("arguments", "")
            thinking = tc.get("thinking", "")
            metrics = get_metrics_collector()
            metrics.inc_tool_call(tool_name)
            tc["_start_time"] = time.perf_counter()
            yield {
                "type": "toolExecuting",
                "tool": tool_name,
                "toolId": tool_id,
                "arguments": arguments,
                "thinking": thinking,
            }
            yield await self._execute_single_tool(tc, messages, session_id, message_index)

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

    async def _analyze_task_complexity(self, user_input: str) -> dict:
        """
        分析任务复杂度

        Returns:
            {"is_complex": bool, "complexity_level": str, "recommended_actions": list}
        """
        # 复杂度关键词检测
        complex_indicators = [
            "多角色",
            "多智能体",
            "协作",
            "多个步骤",
            "复杂任务",
            "帮我规划",
            "需要分析",
            "综合",
            "对比分析",
            "代码生成",
            "系统设计",
            "工作流",
        ]

        simple_indicators = ["简单", "快速", "一句话", "帮我查", "告诉我"]

        # 简单的复杂度检测
        complex_score = sum(1 for kw in complex_indicators if kw in user_input)
        simple_score = sum(1 for kw in simple_indicators if kw in user_input)

        if complex_score > simple_score:
            return {
                "is_complex": True,
                "complexity_level": "high",
                "recommended_actions": ["context_refresher.preserve", "agency_orchestrator.compose_workflow"],
            }

        return {"is_complex": False, "complexity_level": "simple", "recommended_actions": []}

    async def _execute_complexity_recommended_actions(self, session_id: str, recommended_actions: list):
        """执行复杂度分析推荐的行动"""
        for action in recommended_actions:
            if action == "context_refresher.preserve":
                try:
                    # 获取对话历史用于保鲜
                    messages = await self._load_recent_messages(session_id, limit=20)
                    result = await self.skill_handler.execute(
                        "context_refresher", "preserve", {"conversation_history": messages}
                    )
                    inner = result.get("result", result)
                    if inner.get("success"):
                        logger.info("复杂任务：上下文保鲜已触发")
                    else:
                        logger.warning(f"上下文保鲜失败: {inner.get('error')}")
                except Exception as e:
                    logger.warning(f"执行 context_refresher.preserve 异常: {e}")

    async def _load_recent_messages(self, session_id: str, limit: int = 20) -> list:
        """加载最近的对话消息"""
        try:
            vm = VectorMemoryV2()
            results = await vm.search(
                query=f"session:{session_id}",
                collection="conversations",
                n_results=limit,
            )
            # 返回格式: [{"role": "...", "content": "...", ...metadata}]
            return [{"content": r["text"], **r["metadata"]} for r in results]
        except Exception as e:
            logger.warning(f"加载最近消息失败: {e}")
        return []

    async def _maybe_refresh_context(self, session_id: str, messages: list):
        """检查是否需要上下文保鲜"""
        if self._turn_count % self.refresh_interval == 0:
            try:
                result = await self.skill_handler.execute(
                    "context_refresher", "preserve", {"conversation_history": messages[-20:]}
                )
                inner = result.get("result", result)
                if inner.get("success"):
                    logger.info(f"上下文保鲜已触发 (turn {self._turn_count})")
                else:
                    logger.warning(f"上下文保鲜失败: {inner.get('error')}")
            except Exception as e:
                logger.warning(f"上下文保鲜异常: {e}")

    def _update_skill_health(self, tool_name: str, result: dict, elapsed: float):
        """更新技能健康分"""
        # 从工具名提取技能名 (格式: skill_method)
        parts = tool_name.split("_", 1)
        skill_name = parts[0] if len(parts) > 1 else tool_name

        # 判断成功/失败 (支持 jsonrpc 和普通格式)
        # jsonrpc 格式: {"jsonrpc": "2.0", "result": {"success": bool}} 或 {"jsonrpc": "2.0", "error": {...}}
        # 普通格式: {"success": bool, ...}
        if not isinstance(result, dict):
            is_success = False
        else:
            is_jsonrpc_error = "jsonrpc" in result and "error" in result
            inner_result = result.get("result", result)
            inner_success = inner_result.get("success") if isinstance(inner_result, dict) else None
            is_success = not is_jsonrpc_error and (inner_success if inner_success is not None else True)

        # 计算耗时（毫秒）
        duration_ms = elapsed * 1000

        try:
            self.governance.update_health_score(skill_name, is_success, duration_ms)
        except Exception as e:
            logger.debug(f"更新技能健康分失败: {e}")

    async def run_streaming(self, user_input: str, session_id: str = None):
        """流式执行 Agent 循环，yield 事件"""
        metrics = get_metrics_collector()
        start_time = time.perf_counter()

        if session_id is None:
            session_id = "default"

        session_id = await self._prepare_session(user_input, session_id)
        if isinstance(session_id, tuple):
            yield session_id[0]
            return

        messages = await self._build_messages(user_input, session_id)

        for _ in range(self.max_iterations):
            metrics.inc_iteration()
            collected = await self._run_iteration(messages, session_id)
            if collected is None:
                continue

            if not collected["tool_calls_buffer"]:
                duration = time.perf_counter() - start_time
                metrics.record_agent_response_time(duration)
                yield {"type": "done", "content": collected["full_response"]}
                return

            messages.append(self._build_assistant_message(collected["full_response"], collected["tool_calls_buffer"]))
            async for event in self._finalize_iteration(
                session_id, collected["full_response"], collected["tool_calls_buffer"], messages
            ):
                yield event

            self._turn_count += 1
            await self._maybe_refresh_context(session_id, messages)

        duration = time.perf_counter() - start_time
        metrics.record_agent_response_time(duration)
        yield {"type": "done", "content": "达到最大迭代次数"}

    async def _prepare_session(self, user_input: str, session_id: str):
        """准备会话：复杂度分析、图像命令检查、MCP初始化"""
        complexity = await self._analyze_task_complexity(user_input)
        if complexity["is_complex"]:
            logger.info(f"检测到复杂任务: {complexity}")
            await self._execute_complexity_recommended_actions(session_id, complexity.get("recommended_actions", []))

        result = await self._handle_image_command(user_input)
        if result:
            return ({"type": "done", "content": result[1]},)

        await self._ensure_mcp_initialized()
        await self._save_conversation(session_id, "user", user_input)
        return session_id

    async def _run_iteration(self, messages: list, session_id: str):
        """执行单次迭代"""
        collected = None
        async for event in self._collect_stream_events(messages):
            if event.get("type") == "done":
                collected = event
                break
        return collected

    async def _finalize_iteration(self, session_id: str, full_response: str, tool_calls_buffer: list, messages: list):
        """保存助手响应并执行工具调用"""
        message_index = None
        # 如果有内容或有待执行的工具调用，都需要保存助手消息
        if full_response or tool_calls_buffer:
            filtered_response = filter_think_tags(full_response)
            # 如果过滤后为空但有工具调用，保存原始响应以确保 message_index 被设置
            content_to_save = filtered_response if filtered_response else (full_response or " ")
            loop = asyncio.get_running_loop()
            message_index = await loop.run_in_executor(
                None, self._save_conversation_sync, session_id, "assistant", content_to_save
            )

        yield {"type": "tool_call_start", "count": len(tool_calls_buffer), "message_index": message_index}

        async for event in self._execute_tool_calls(tool_calls_buffer, messages, session_id, message_index):
            yield event
