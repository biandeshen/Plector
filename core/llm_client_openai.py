# mypy: ignore-errors
"""
LLM 客户端 - OpenAI 兼容实现（OpenAI / MiniMax 等）
"""

import json
import logging
import time
from collections.abc import AsyncIterator

from .llm_client_base import LLMClientBase

logger = logging.getLogger(__name__)


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
        try:
            response = await client.chat.completions.create(**kwargs, timeout=self.provider_config.get("timeout", 60))
        except Exception:
            logger.exception("OpenAI chat() failed")
            raise
        duration = time.perf_counter() - start_time
        self._record_metrics(messages, duration)

        msg = response.choices[0].message
        return self._normalize_message(msg)

    async def stream_chat(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncIterator[dict]:
        """流式聊天"""
        client = self._get_client()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        start_time = time.perf_counter()
        content = ""
        tool_buffer: list[dict] = []
        emitted_indices: set[int] = set()
        text_buffer: list[str] = []

        stream = await client.chat.completions.create(**kwargs, timeout=self.provider_config.get("timeout", 60))
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                content += delta.content
                text_buffer.append(delta.content)
                if len("".join(text_buffer)) >= 30:
                    yield {"type": "content", "content": "".join(text_buffer)}
                    text_buffer = []

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    index = tc.index if tc.index is not None else 0
                    self._openai_append_tc(tc, index, tool_buffer, emitted_indices)

        if text_buffer:
            yield {"type": "content", "content": "".join(text_buffer)}

        for index, buf in enumerate(tool_buffer):
            if index not in emitted_indices:
                try:
                    json.loads(buf["function"]["arguments"])
                    emitted_indices.add(index)
                except json.JSONDecodeError:
                    pass

        duration = time.perf_counter() - start_time
        self._record_metrics(messages, duration)
        yield {"type": "done", "content": content, "tool_calls": tool_buffer or None}

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
