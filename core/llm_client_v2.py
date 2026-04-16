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
from collections.abc import AsyncIterator

from dotenv import load_dotenv

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

    # ========== 非流量 chat（保持兼容）==========

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """发送聊天请求，返回统一格式: {"content": str, "tool_calls": list|None}"""
        if self.provider == "ollama":
            return await self._ollama_chat(messages, tools)
        elif self.provider == "openai":
            return await self._openai_chat(messages, tools)
        elif self.provider == "anthropic":
            return await self._anthropic_chat(messages, tools)
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")

    # ========== 流量接口 ==========

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """流量聊天，返回 AsyncIterator[dict]"""
        if self.provider == "ollama":
            async for chunk in self._ollama_stream(messages, tools):
                yield chunk
        elif self.provider == "openai":
            async for chunk in self._openai_stream(messages, tools):
                yield chunk
        elif self.provider == "anthropic":
            async for chunk in self._anthropic_stream(messages, tools):
                yield chunk
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")

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

        async for response in client.chat(**kwargs):
            msg = response.get("message", {})
            delta = msg.get("content", "")
            if delta:
                content += delta
                yield {"type": "content", "content": delta}

            tcs = msg.get("tool_calls")
            if tcs:
                tool_calls = tcs
                yield {"type": "tool_call", "tool_call": tcs[0]}

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
        tool_calls = None

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                # 过滤 thinking tokens (<think>/</think>)
                text = delta.content
                if "<think>" in text:
                    text = self._strip_thinking(text)
                if text:  # 只在没有完全过滤掉时 yield
                    content += text
                    yield {"type": "content", "content": text}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": json.dumps(tc.function.arguments) if isinstance(tc.function.arguments, dict) else tc.function.arguments,
                        },
                    })
                    yield {"type": "tool_call", "tool_call": tool_calls[-1]}

        yield {"type": "done", "content": self._strip_thinking(content), "tool_calls": tool_calls}

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """过滤掉 thinking tokens (<think>/</think>)"""
        import re
        # 移除 <think>...</think> 块
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
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
                        "arguments": json.dumps(tc.function.arguments) if isinstance(tc.function.arguments, dict) else tc.function.arguments,
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
        system, user_messages = self._split_system(messages)

        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "max_tokens": 4096,
            "messages": user_messages,
            "stream": True,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools_for_anthropic(tools)

        content = ""
        tool_calls = None

        async with client.messages.stream(**kwargs) as stream:
            async for chunk in stream:
                if chunk.type == "content_block_delta":
                    delta = chunk.delta
                    if delta.type == "text_delta":
                        content += delta.text
                        yield {"type": "content", "content": delta.text}

        # Anthropic 流量结束后手动构造 tool_calls
        async with client.messages.stream(**kwargs) as stream:
            async for chunk in stream:
                if chunk.type == "content_block_start":
                    cb = chunk.content_block
                    if cb.type == "tool_use" and tool_calls is None:
                        tool_calls = []
                        tool_calls.append({
                            "id": cb.id,
                            "function": {
                                "name": cb.name,
                                "arguments": "",
                            },
                        })
                elif chunk.type == "content_block_delta":
                    delta = chunk.delta
                    if delta.type == "input_json_delta" and tool_calls:
                        tool_calls[-1]["function"]["arguments"] += delta.partial_json

        yield {"type": "done", "content": content, "tool_calls": tool_calls}

    def _split_system(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """分离 system 消息"""
        system_parts = []
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                user_messages.append(msg)
        return "\n\n".join(system_parts) if system_parts else "", user_messages

    def _normalize_anthropic_response(self, response) -> dict:
        """标准化 Anthropic 响应"""
        content = ""
        tool_calls = None
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if not tool_calls:
                    tool_calls = []
                tool_calls.append({
                    "id": block.id,
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })
        return {"content": content, "tool_calls": tool_calls}

    def _convert_tools_for_anthropic(self, tools: list[dict]) -> list[dict]:
        """转换工具格式为 Anthropic 格式"""
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"],
            }
            for tool in tools
        ]

    def _get_env(self, value: str | None) -> str:
        """支持 ${ENV_VAR} 格式的环境变量引用"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            return os.environ.get(value[2:-1], "")
        return value or ""


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
    """流量打印响应（带光标控制）"""
    cursor = ""

    async for chunk in client.stream_chat(messages, tools):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
            cursor += chunk["content"]
        elif chunk["type"] == "done":
            print()
            return {"content": chunk["content"], "tool_calls": chunk.get("tool_calls")}

    return {"content": cursor, "tool_calls": None}
