# mypy: ignore-errors
"""
LLM 客户端 - Anthropic 实现
"""

import json
import logging
import time
from collections.abc import AsyncIterator

from .llm_client_base import LLMClientBase

logger = logging.getLogger(__name__)


class AnthropicClient(LLMClientBase):
    """Anthropic LLM 客户端"""

    def __init__(self, config: dict):
        super().__init__(config)

    def _get_client(self):
        """获取或创建 Anthropic 客户端"""
        if "anthropic" not in self._clients:
            import anthropic

            self._clients["anthropic"] = anthropic.AsyncAnthropic(
                api_key=self._get_env(self.provider_config.get("api_key")),
            )
        return self._clients["anthropic"]

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """非流式聊天"""
        client = self._get_client()
        system, user_messages = self._split_system(messages)

        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "max_tokens": self.provider_config.get("max_tokens", 4096),
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        start_time = time.perf_counter()
        try:
            response = await client.messages.create(**kwargs, timeout=self.provider_config.get("timeout", 60))
        except Exception:
            logger.exception("Anthropic chat() failed")
            raise
        duration = time.perf_counter() - start_time
        self._record_metrics(messages, duration)

        return self._normalize_response(response)

    async def stream_chat(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncIterator[dict]:
        """流式聊天"""
        client = self._get_client()
        kwargs = self._build_stream_kwargs(messages, tools)

        start_time = time.perf_counter()
        content = ""
        tool_buffer: list[dict] = []
        emitted_indices: set[int] = set()
        text_buffer: list[str] = []

        async with client.messages.stream(**kwargs, timeout=self.provider_config.get("timeout", 60)) as stream:
            async for chunk in stream:
                event = self._process_chunk(chunk, text_buffer, tool_buffer, emitted_indices)
                if event:
                    yield event
                    if event["type"] == "content":
                        content += event["content"]

        for event in self._emit_remaining(text_buffer, tool_buffer, emitted_indices):
            yield event

        duration = time.perf_counter() - start_time
        self._record_metrics(messages, duration)
        yield {"type": "done", "content": content, "tool_calls": tool_buffer if tool_buffer else None}

    def _build_stream_kwargs(self, messages: list[dict], tools: list[dict] | None) -> dict:
        """构建流式请求参数"""
        system, user_messages = self._split_system(messages)
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "max_tokens": self.provider_config.get("max_tokens", 4096),
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        return kwargs

    def _process_chunk(
        self, chunk, text_buffer: list[str], tool_buffer: list[dict], emitted_indices: set[int]
    ) -> dict | None:
        """处理单个流式块"""
        if chunk.type == "content_block_delta":
            delta = chunk.delta
            if delta.type == "text_delta":
                return self._handle_text_delta(delta, text_buffer)
            elif delta.type == "input_json_delta":
                return self._handle_tool_delta(delta, tool_buffer, emitted_indices)
        elif chunk.type == "content_block_start":
            return self._handle_block_start(chunk, text_buffer, tool_buffer)
        return None

    def _handle_text_delta(self, delta, text_buffer: list[str]) -> dict | None:
        """处理 text_delta"""
        text_buffer.append(delta.text)
        if len("".join(text_buffer)) >= 30:
            result = "".join(text_buffer)
            text_buffer.clear()
            return {"type": "content", "content": result}
        return None

    def _handle_tool_delta(self, delta, tool_buffer: list[dict], emitted_indices: set[int]) -> dict | None:
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

    def _handle_block_start(self, chunk, text_buffer: list[str], tool_buffer: list[dict]) -> dict | None:
        """处理 content_block_start"""
        if text_buffer:
            result = "".join(text_buffer)
            text_buffer.clear()
            return {"type": "content", "content": result}
        cb = chunk.content_block
        if cb.type == "tool_use":
            tool_buffer.append({"id": cb.id, "function": {"name": cb.name, "arguments": ""}})
        return None

    def _emit_remaining(self, text_buffer: list[str], tool_buffer: list[dict], emitted_indices: set[int]) -> list[dict]:
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

    def _normalize_response(self, response) -> dict:
        """标准化响应"""
        content = ""
        thinking = ""
        tool_calls: list[dict] | None = None
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "thinking":
                thinking += block.thinking
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
        return {"content": content, "thinking": thinking if thinking else None, "tool_calls": tool_calls}

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """转换工具格式"""
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"],
            }
            for tool in tools
        ]
