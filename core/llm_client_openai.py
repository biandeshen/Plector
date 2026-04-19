"""
LLM 客户端 - OpenAI 兼容实现（OpenAI / MiniMax 等）
"""

import json
import time
from collections.abc import AsyncIterator

from .llm_client_base import LLMClientBase


class OpenAIClient(LLMClientBase):
    """OpenAI 兼容 LLM 客户端"""

    def __init__(self, config: dict, provider: str = "openai"):
        super().__init__(config)
        self._provider = provider

    def _get_client(self):
        """获取或创建客户端"""
        if self._provider not in self._clients:
            from openai import AsyncOpenAI

            self._clients[self._provider] = AsyncOpenAI(
                api_key=self._get_env(self.provider_config.get("api_key")),
                base_url=self.provider_config.get("base_url"),
            )
        return self._clients[self._provider]

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """非流式聊天"""
        client = self._get_client()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        start_time = time.perf_counter()
        response = await client.chat.completions.create(**kwargs)
        duration = time.perf_counter() - start_time
        self._record_metrics(messages, duration)

        msg = response.choices[0].message
        return self._normalize_message(msg)

    async def stream_chat(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncIterator[dict]:
        """流式聊天"""
        client = self._get_client()
        kwargs = self._make_stream_kwargs(messages, tools)
        start_time = time.perf_counter()
        result = {"content": "", "tool_calls": []}
        result = await self._openai_stream(client, kwargs)
        duration = time.perf_counter() - start_time
        self._record_metrics(messages, duration)
        yield {"type": "done", "content": result["content"], "tool_calls": result["tool_calls"]}

    def _make_stream_kwargs(self, messages: list[dict], tools: list[dict] | None) -> dict:
        """构建流式请求参数"""
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
        return kwargs

    async def _openai_stream(self, client, kwargs: dict) -> dict:
        """OpenAI 流式处理"""
        content = ""
        tool_buffer: list[dict] = []
        emitted_indices: set[int] = set()
        text_buffer: list[str] = []

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            content, tool_buffer, emitted_indices, text_buffer = self._openai_handle_chunk(
                chunk, content, tool_buffer, emitted_indices, text_buffer
            )

        return {"content": content, "tool_calls": tool_buffer}

    def _openai_handle_chunk(
        self, chunk, content: str, tool_buffer: list[dict], emitted_indices: set[int], text_buffer: list[str]
    ) -> tuple[str, list[dict], set[int], list[str]]:
        """处理 OpenAI 流式块"""
        if not chunk.choices:
            return content, tool_buffer, emitted_indices, text_buffer

        delta = chunk.choices[0].delta
        if delta.content:
            text = delta.content
            if text:
                content += text
                text_buffer.append(text)
                if len("".join(text_buffer)) >= 30:
                    pass  # 批量发送由调用方处理

        if delta.tool_calls:
            for tc in delta.tool_calls:
                index = tc.index if tc.index is not None else 0
                self._openai_append_tc(tc, index, tool_buffer, emitted_indices)

        return content, tool_buffer, emitted_indices, text_buffer

    def _openai_append_tc(self, tc, index: int, tool_buffer: list[dict], emitted_indices: set[int]) -> None:
        """追加 tool_call"""
        if index >= len(tool_buffer):
            tool_buffer.append({"id": tc.id or f"call_{index}", "function": {"name": "", "arguments": ""}})
        if tc.function and tc.function.name:
            tool_buffer[index]["function"]["name"] = tc.function.name
        if tc.id:
            tool_buffer[index]["id"] = tc.id

    def _normalize_message(self, msg) -> dict:
        """标准化消息格式"""
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
        filtered, thinking = self._strip_thinking(msg.content or "")
        return {"content": filtered, "thinking": thinking, "tool_calls": tool_calls}
