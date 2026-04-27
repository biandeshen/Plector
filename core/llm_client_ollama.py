"""
LLM 客户端 - Ollama 实现
"""

import time
from collections.abc import AsyncIterator

from .llm_client_base import LLMClientBase


class OllamaClient(LLMClientBase):
    """Ollama LLM 客户端"""

    def __init__(self, config: dict):
        super().__init__(config)

    def _get_client(self):
        """获取或创建 Ollama 客户端"""
        if "ollama" not in self._clients:
            import ollama

            self._clients["ollama"] = ollama.AsyncClient(
                host=self.provider_config.get("host", "http://localhost:11434")
            )
        return self._clients["ollama"]

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
        response = await client.chat(**kwargs)
        duration = time.perf_counter() - start_time
        self._record_metrics(messages, duration)

        return {
            "content": response.get("message", {}).get("content", ""),
            "tool_calls": response.get("message", {}).get("tool_calls"),
        }

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
        tool_calls = None
        text_buffer: list[str] = []

        async for response in client.chat(**kwargs):
            msg = response.get("message", {})
            delta = msg.get("content", "")
            if delta:
                content += delta
                text_buffer.append(delta)
                if len("".join(text_buffer)) >= 30:
                    yield {"type": "content", "content": "".join(text_buffer)}
                    text_buffer = []

            tcs = msg.get("tool_calls")
            if tcs:
                tool_calls = tcs
                yield {"type": "tool_call", "tool_call": tcs[0]}

        if text_buffer:
            yield {"type": "content", "content": "".join(text_buffer)}

        duration = time.perf_counter() - start_time
        self._record_metrics(messages, duration)
        yield {"type": "done", "content": content, "tool_calls": tool_calls}
