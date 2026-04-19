"""
LLM 客户端 v2 - 流量响应支持
===========================
支持多后端（Ollama、OpenAI、Anthropic、MiniMax）的流量响应

使用方式:
    from core.llm_client_v2 import LLMClientV2

    # 非流量
    result = await client.chat(messages, tools)

    # 流量
    async for chunk in client.stream_chat(messages):
        print(chunk, end="", flush=True)
"""

from collections.abc import AsyncIterator

from .llm_client_anthropic import AnthropicClient
from .llm_client_minimax import MiniMaxClient
from .llm_client_ollama import OllamaClient
from .llm_client_openai import OpenAIClient


class LLMClientV2:
    """LLM 客户端 v2，支持流量响应 - 门面类"""

    def __init__(self, config: dict):
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model", "qwen3:4b")
        self.provider_config = config.get(self.provider, {})
        self._client = self._create_client()

    def _create_client(self):
        """根据 provider 创建对应的客户端"""
        if self.provider == "ollama":
            return OllamaClient({"provider": self.provider, "ollama": self.provider_config, "model": self.model})
        elif self.provider == "openai":
            return OpenAIClient({"provider": self.provider, "openai": self.provider_config, "model": self.model})
        elif self.provider == "anthropic":
            return AnthropicClient({"provider": self.provider, "anthropic": self.provider_config, "model": self.model})
        elif self.provider == "minimax":
            return MiniMaxClient({"provider": self.provider, "minimax": self.provider_config, "model": self.model})
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """发送聊天请求"""
        return await self._client.chat(messages, tools)

    async def stream_chat(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncIterator[dict]:
        """流式聊天"""
        async for chunk in self._client.stream_chat(messages, tools):
            yield chunk


# ========== 单例模式 ==========

_llm_client_v2_instance: LLMClientV2 | None = None


def get_llm_client_v2(config: dict | None = None) -> LLMClientV2:
    """获取 LLMClientV2 单例实例"""
    global _llm_client_v2_instance
    if _llm_client_v2_instance is None:
        if config is None:
            config = {}
        _llm_client_v2_instance = LLMClientV2(config)
    return _llm_client_v2_instance


def reset_llm_client_v2() -> None:
    """重置单例实例（用于测试）"""
    global _llm_client_v2_instance
    _llm_client_v2_instance = None


# ========== 便携函数 ==========


async def stream_print(client: LLMClientV2, messages: list[dict], tools: list[dict] | None = None):
    """流式打印响应（带光标控制）"""
    cursor = ""

    async for chunk in client.stream_chat(messages, tools):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
            cursor += chunk["content"]
        elif chunk["type"] == "done":
            print()
            return {"content": chunk["content"], "tool_calls": chunk.get("tool_calls")}

    return {"content": cursor, "tool_calls": None}
