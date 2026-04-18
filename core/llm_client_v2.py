"""
LLM 客户端 v2 - 流量响应支持
===========================
支持多后端（Ollama、OpenAI、Anthropic）的流量响应

使用方式:
    from core.llm_client_v2 import LLMClientV2

    # 非流量
    result = await client.chat(messages, tools)

    # 流量
    async for chunk in client.stream_chat(messages):
        print(chunk, end="", flush=True)
"""

import json
import os
import time
from collections.abc import AsyncIterator

from dotenv import load_dotenv

from .metrics import get_metrics_collector

load_dotenv()


class LLMClientV2:
    """LLM 客户端 v2，支持流量响应"""

    def __init__(self, config: dict):
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model", "qwen3:4b")
        self.provider_config = config.get(self.provider, {})
        self._clients = {}

    # ========== 客户端获取 ==========

    def _get_ollama_client(self):
        if "ollama" not in self._clients:
            import ollama

            self._clients["ollama"] = ollama.AsyncClient(
                host=self.provider_config.get("host", "http://localhost:11434")
            )
        return self._clients["ollama"]

    def _get_openai_client(self):
        if "openai" not in self._clients:
            from openai import AsyncOpenAI

            self._clients["openai"] = AsyncOpenAI(
                api_key=self._get_env(self.provider_config.get("api_key")),
                base_url=self.provider_config.get("base_url"),
            )
        return self._clients["openai"]

    def _get_anthropic_client(self):
        if "anthropic" not in self._clients:
            import anthropic

            self._clients["anthropic"] = anthropic.AsyncAnthropic(
                api_key=self._get_env(self.provider_config.get("api_key")),
            )
        return self._clients["anthropic"]

    def _get_minimax_client(self):
        if "minimax" not in self._clients:
            from openai import AsyncOpenAI

            self._clients["minimax"] = AsyncOpenAI(
                api_key=self._get_env(self.provider_config.get("api_key")),
                base_url=self.provider_config.get("base_url", "https://api.minimax.chat/v1"),
            )
        return self._clients["minimax"]

    # ========== 非流量 chat（保持兼容）==========

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """
        发送聊天请求，返回统一格式: {"content": str, "tool_calls": list|None}
        """
        metrics = get_metrics_collector()
        metrics.inc_llm_request()
        start_time = time.perf_counter()
        try:
            if self.provider == "ollama":
                result = await self._ollama_chat(messages, tools)
            elif self.provider == "openai":
                result = await self._openai_chat(messages, tools)
            elif self.provider == "anthropic":
                result = await self._anthropic_chat(messages, tools)
            elif self.provider == "minimax":
                result = await self._minimax_chat(messages, tools)
            else:
                raise ValueError(f"不支持的 provider: {self.provider}")

            duration = time.perf_counter() - start_time
            metrics.record_llm_latency(duration)

            # Estimate token usage based on message content length
            total_chars = sum(len(m.get("content", "")) for m in messages)
            estimated_tokens = int(total_chars / 4)  # Rough estimation
            if estimated_tokens > 0:
                metrics.inc_tokens(estimated_tokens)

            return result
        except Exception:
            metrics.inc_llm_error()
            raise

    # ========== 流量接口 ==========

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """
        流量聊天，返回 AsyncIterator[dict]
        """
        metrics = get_metrics_collector()
        metrics.inc_llm_request()
        start_time = time.perf_counter()
        total_chars = 0

        try:
            if self.provider == "ollama":
                async for chunk in self._ollama_stream(messages, tools):
                    total_chars += len(chunk.get("content", ""))
                    yield chunk
            elif self.provider == "openai":
                async for chunk in self._openai_stream(messages, tools):
                    total_chars += len(chunk.get("content", ""))
                    yield chunk
            elif self.provider == "anthropic":
                async for chunk in self._anthropic_stream(messages, tools):
                    total_chars += len(chunk.get("content", ""))
                    yield chunk
            elif self.provider == "minimax":
                async for chunk in self._minimax_stream(messages, tools):
                    total_chars += len(chunk.get("content", ""))
                    yield chunk
            else:
                raise ValueError(f"不支持的 provider: {self.provider}")

            duration = time.perf_counter() - start_time
            metrics.record_llm_latency(duration)

            # Estimate token usage
            estimated_tokens = int(total_chars / 4)
            if estimated_tokens > 0:
                metrics.inc_tokens(estimated_tokens)

        except Exception:
            metrics.inc_llm_error()
            raise

    # ========== Ollama 实现 ==========

    async def _ollama_chat(self, messages, tools):
        client = self._get_ollama_client()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        response = await client.chat(**kwargs)
        return {
            "content": response.get("message", {}).get("content", ""),
            "tool_calls": response.get("message", {}).get("tool_calls"),
        }

    async def _ollama_stream(self, messages, tools) -> AsyncIterator[dict]:
        client = self._get_ollama_client()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        content = ""
        tool_calls = None
        text_buffer: list[str] = []  # 文本缓冲，减少网络碎片

        async for response in client.chat(**kwargs):
            msg = response.get("message", {})
            delta = msg.get("content", "")
            if delta:
                content += delta
                text_buffer.append(delta)
                # 批量发送：累积至少 30 字符再发送
                if len("".join(text_buffer)) >= 30:
                    yield {"type": "content", "content": "".join(text_buffer)}
                    text_buffer = []

            tcs = msg.get("tool_calls")
            if tcs:
                tool_calls = tcs
                yield {"type": "tool_call", "tool_call": tcs[0]}

        # 流结束时发送剩余缓冲
        if text_buffer:
            yield {"type": "content", "content": "".join(text_buffer)}

        yield {"type": "done", "content": content, "tool_calls": tool_calls}

    # ========== OpenAI 实现 ==========

    async def _openai_chat(self, messages, tools):
        client = self._get_openai_client()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        response = await client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        return self._normalize_openai_message(msg)

    def _openai_process_tool_call_delta(self, tc, index: int, tool_buffer: list[dict], emitted_indices: set[int]):
        """处理 OpenAI tool_call delta，返回要 emit 的 tool_call 或 None"""
        self._openai_append_tool_call(tc, index, tool_buffer)
        if tc.function and tc.function.arguments:
            raw_args = tc.function.arguments
            if isinstance(raw_args, dict):
                raw_args = json.dumps(raw_args)
            tool_buffer[index]["function"]["arguments"] += raw_args
        elif index not in emitted_indices:
            emitted_indices.add(index)
            return tool_buffer[index]
        return None

    async def _openai_stream(self, messages, tools) -> AsyncIterator[dict]:
        client = self._get_openai_client()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        content = ""
        tool_buffer: list[dict] = []
        emitted_indices: set[int] = set()
        text_buffer: list[str] = []

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                text = delta.content
                if text:
                    content += text
                    text_buffer.append(text)
                    if len("".join(text_buffer)) >= 30:
                        yield {"type": "content", "content": "".join(text_buffer)}
                        text_buffer = []

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    index = tc.index if tc.index is not None else 0
                    emitted_tc = self._openai_process_tool_call_delta(tc, index, tool_buffer, emitted_indices)
                    if emitted_tc:
                        yield {"type": "tool_call", "tool_call": emitted_tc}

        if text_buffer:
            yield {"type": "content", "content": "".join(text_buffer)}

        for index, buf in enumerate(tool_buffer):
            if index not in emitted_indices:
                try:
                    json.loads(buf["function"]["arguments"])
                    emitted_indices.add(index)
                except json.JSONDecodeError:
                    pass

        yield {"type": "done", "content": content, "tool_calls": tool_buffer if tool_buffer else None}

    def _openai_append_tool_call(self, tc, index: int, tool_buffer: list[dict]) -> None:
        """﹏﹟追加 tool_call 到缓冲器﹟﹏"""
        if index >= len(tool_buffer):
            tool_buffer.append({"id": tc.id or f"call_{index}", "function": {"name": "", "arguments": ""}})
        if tc.function and tc.function.name:
            tool_buffer[index]["function"]["name"] = tc.function.name
        if tc.id:
            tool_buffer[index]["id"] = tc.id

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """
        过滤掉 thinking tokens (﹏﹟/﹟)

        处理三种情况：
        1. 完整的 ﹏﹟...﹟ 块
        2. 只有开始标签 ﹏﹟ 没有结束标签
        3. 只有结束标签 ﹟ 没有开始标签（理论上不会发生）
        """
        import re

        # 首先移除完整的 ﹏﹟...﹟ 块
        text = re.sub(r"﹏﹟.*?﹟", "", text, flags=re.DOTALL)

        # 移除独立的 ﹏﹟ 标签及其后续内容（直到下一个可能的 ﹟ 或行尾）
        # 使用贪婪匹配来移除整个不完整的 thinking 块
        text = re.sub(r"﹏﹟.*$", "", text, flags=re.MULTILINE)

        return text.strip()

    def _normalize_openai_message(self, msg) -> dict:
        """标准化 OpenAI 消息格式"""
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": json.dumps(tc.function.arguments)
                        if isinstance(tc.function.arguments, dict)
                        else tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return {"content": self._strip_thinking(msg.content or ""), "tool_calls": tool_calls}

    # ========== Anthropic 实现 ==========

    async def _anthropic_chat(self, messages, tools):
        client = self._get_anthropic_client()
        system, user_messages = self._split_system(messages)

        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "max_tokens": 4096,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools_for_anthropic(tools)

        response = await client.messages.create(**kwargs)
        return self._normalize_anthropic_response(response)

    async def _anthropic_stream(self, messages, tools) -> AsyncIterator[dict]:
        client = self._get_anthropic_client()
        kwargs = self._anthropic_build_stream_kwargs(messages, tools)

        content = ""
        tool_buffer: list[dict] = []
        emitted_indices: set[int] = set()
        text_buffer: list[str] = []

        async with client.messages.stream(**kwargs) as stream:
            async for chunk in stream:
                event = self._anthropic_process_chunk(chunk, text_buffer, tool_buffer, emitted_indices)
                if event:
                    yield event
                    if event["type"] == "content":
                        content += event["content"]

        for event in self._anthropic_emit_remaining(text_buffer, tool_buffer, emitted_indices):
            yield event

        yield {"type": "done", "content": content, "tool_calls": tool_buffer if tool_buffer else None}

    def _anthropic_build_stream_kwargs(self, messages, tools) -> dict:
        """构建 Anthropic 流式请求参数"""
        system, user_messages = self._split_system(messages)
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "max_tokens": 4096,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools_for_anthropic(tools)
        return kwargs

    def _anthropic_process_chunk(self, chunk, text_buffer, tool_buffer, emitted_indices) -> dict | None:
        """处理单个流式块，返回要 emit 的事件或 None"""
        if chunk.type == "content_block_delta":
            delta = chunk.delta
            if delta.type == "text_delta":
                return self._anthropic_handle_text_delta(delta, text_buffer)
            elif delta.type == "input_json_delta":
                return self._anthropic_handle_tool_delta(delta, tool_buffer, emitted_indices)
        elif chunk.type == "content_block_start":
            return self._anthropic_handle_block_start(chunk, text_buffer, tool_buffer)
        return None

    def _anthropic_handle_text_delta(self, delta, text_buffer) -> dict | None:
        """处理 text_delta"""
        text_buffer.append(delta.text)
        if len("".join(text_buffer)) >= 30:
            result = "".join(text_buffer)
            text_buffer.clear()
            return {"type": "content", "content": result}
        return None

    def _anthropic_handle_tool_delta(self, delta, tool_buffer, emitted_indices) -> dict | None:
        """处理 input_json_delta"""
        if not tool_buffer:
            return None
        index = len(tool_buffer) - 1
        tool_buffer[index]["function"]["arguments"] += delta.partial_json
        try:
            json.loads(tool_buffer[index]["function"]["arguments"])
            if index not in emitted_indices:
                emitted_indices.add(index)
                return {"type": "tool_call", "tool_call": tool_buffer[index]}
        except json.JSONDecodeError:
            pass
        return None

    def _anthropic_handle_block_start(self, chunk, text_buffer, tool_buffer) -> dict | None:
        """处理 content_block_start"""
        if text_buffer:
            result = "".join(text_buffer)
            text_buffer.clear()
            return {"type": "content", "content": result}
        cb = chunk.content_block
        if cb.type == "tool_use":
            tool_buffer.append({"id": cb.id, "function": {"name": cb.name, "arguments": ""}})
        return None

    def _anthropic_emit_remaining(self, text_buffer, tool_buffer, emitted_indices) -> list[dict]:
        """发送剩余缓冲"""
        events = []
        if text_buffer:
            events.append({"type": "content", "content": "".join(text_buffer)})
        for index, buf in enumerate(tool_buffer):
            if index not in emitted_indices:
                try:
                    json.loads(buf["function"]["arguments"])
                    emitted_indices.add(index)
                    events.append({"type": "tool_call", "tool_call": buf})
                except json.JSONDecodeError:
                    pass
        return events

    def _split_system(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """
        分离 system 消息
        """
        system_parts = []
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                user_messages.append(msg)
        return "\n\n".join(system_parts) if system_parts else "", user_messages

    def _normalize_anthropic_response(self, response) -> dict:
        """
        标准化 Anthropic 响应
        """
        content = ""
        tool_calls: list[dict] | None = None
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if not tool_calls:
                    tool_calls = []
                tool_calls.append(
                    {
                        "id": block.id,
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    }
                )
        return {"content": content, "tool_calls": tool_calls}

    def _convert_tools_for_anthropic(self, tools: list[dict]) -> list[dict]:
        """
        转换工具格式为 Anthropic 格式
        """
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"],
            }
            for tool in tools
        ]

    # ========== MiniMax 实现（OpenAI 兼容）==========

    async def _minimax_chat(self, messages, tools):
        """﹏﹟MiniMax 聊天（非流式）﹟﹏"""
        client = self._get_minimax_client()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        response = await client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        return self._normalize_openai_message(msg)

    async def _minimax_stream(self, messages, tools) -> AsyncIterator[dict]:
        """﹏﹟MiniMax 聊天（流式）﹟﹏"""
        client = self._get_minimax_client()
        kwargs = self._minimax_build_stream_kwargs(messages, tools)

        content = ""
        tool_buffer: list[dict] = []
        emitted_indices: set[int] = set()
        text_buffer: list[str] = []

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            event = self._minimax_process_chunk(chunk, text_buffer, tool_buffer, emitted_indices)
            if event:
                yield event
                if event["type"] == "content":
                    content += event["content"]

        if text_buffer:
            remaining = {"type": "content", "content": "".join(text_buffer)}
            content += remaining["content"]
            yield remaining

        for event in self._minimax_emit_remaining(tool_buffer, emitted_indices):
            yield event

        yield {"type": "done", "content": content, "tool_calls": tool_buffer if tool_buffer else None}

    def _minimax_build_stream_kwargs(self, messages, tools) -> dict:
        """构建 MiniMax 流式请求参数"""
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
        return kwargs

    def _minimax_process_chunk(self, chunk, text_buffer, tool_buffer, emitted_indices) -> dict | None:
        """处理单个流式块"""
        if not chunk.choices:
            return None
        delta = chunk.choices[0].delta

        if delta.content:
            text = delta.content
            if text:
                text_buffer.append(text)
                if len("".join(text_buffer)) >= 30:
                    result = {"type": "content", "content": "".join(text_buffer)}
                    text_buffer.clear()
                    return result

        if delta.tool_calls:
            for tc in delta.tool_calls:
                return self._minimax_process_tool_call(tc, tool_buffer, emitted_indices)
        return None

    def _minimax_process_tool_call(self, tc, tool_buffer, emitted_indices) -> dict | None:
        """处理 tool_call"""
        index = tc.index if tc.index is not None else 0
        self._openai_append_tool_call(tc, index, tool_buffer)
        if tc.function and tc.function.arguments:
            raw_args = tc.function.arguments
            if isinstance(raw_args, dict):
                raw_args = json.dumps(raw_args)
            tool_buffer[index]["function"]["arguments"] += raw_args
        elif index not in emitted_indices:
            emitted_indices.add(index)
            return {"type": "tool_call", "tool_call": tool_buffer[index]}
        return None

    def _minimax_emit_remaining(self, tool_buffer, emitted_indices) -> list[dict]:
        """发送剩余缓冲"""
        events = []
        for index, buf in enumerate(tool_buffer):
            if index not in emitted_indices:
                try:
                    json.loads(buf["function"]["arguments"])
                    emitted_indices.add(index)
                except json.JSONDecodeError:
                    pass
        return events

    def _get_env(self, value: str | None) -> str:
        """
        支持 ${ENV_VAR} 格式的环境变量引用
        """
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            return os.environ.get(value[2:-1], "")
        return value or ""


# ========== 单例模式 ==========

_llm_client_v2_instance: LLMClientV2 | None = None


def get_llm_client_v2(config: dict | None = None) -> LLMClientV2:
    """
    获取 LLMClientV2 单例实例
    """
    global _llm_client_v2_instance
    if _llm_client_v2_instance is None:
        if config is None:
            config = {}
        _llm_client_v2_instance = LLMClientV2(config)
    return _llm_client_v2_instance


def reset_llm_client_v2() -> None:
    """
    重置单例实例（用于测试）
    """
    global _llm_client_v2_instance
    _llm_client_v2_instance = None


# ========== 便携函数 ==========


async def stream_print(client: LLMClientV2, messages: list[dict], tools: list[dict] | None = None):
    """
    流量打印响应（带光标控制）
    """
    cursor = ""

    async for chunk in client.stream_chat(messages, tools):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
            cursor += chunk["content"]
        elif chunk["type"] == "done":
            print()
            return {"content": chunk["content"], "tool_calls": chunk.get("tool_calls")}

    return {"content": cursor, "tool_calls": None}
