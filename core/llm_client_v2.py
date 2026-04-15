"""
LLM 客户端 v2 - 流式响应支持
===========================
支持多后端（Ollama、OpenAI、Anthropic）的流式响应

使用方式:
    from core.llm_client_v2 import LLMClientV2
    
    # 非流式
    result = await client.chat(messages, tools)
    
    # 流式
    async for chunk in client.stream_chat(messages):
        print(chunk, end="", flush=True)
"""

import json
import os
from typing import AsyncIterator

from dotenv import load_dotenv

load_dotenv()


class LLMClientV2:
    """LLM 客户端 v2，支持流式响应"""

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

    # ========== 非流式 chat（保持兼容）==========

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

    # ========== 流式接口 ==========

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """
        流式聊天，返回 AsyncIterator[dict]
        
        每条消息格式:
            {"type": "content", "content": str}
            {"type": "tool_call", "tool_call": {...}}
            {"type": "done", "content": str, "tool_calls": list|None}
        """
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
            
            # 工具调用
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

        async for chunk in await client.chat.completions.create(**kwargs):
            delta = chunk.choices[0].delta
            
            # 文本内容
            if delta.content:
                content += delta.content
                yield {"type": "content", "content": delta.content}
            
            # 工具调用
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })
                    yield {"type": "tool_call", "tool_call": tool_calls[-1]}

        yield {"type": "done", "content": content, "tool_calls": tool_calls}

    def _normalize_openai_message(self, msg) -> dict:
        """标准化 OpenAI 消息格式"""
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return {
            "content": msg.content or "",
            "tool_calls": tool_calls,
        }

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
                # 文本块
                if chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        content += chunk.delta.text
                        yield {"type": "content", "content": chunk.delta.text}
                    elif chunk.delta.type == "input_json_delta":
                        # 工具参数增量（不单独 yield）
                        pass
                
                # 工具调用块
                elif chunk.type == "message_delta":
                    # 最终消息增量
                    pass

        # Anthropic 流式结束后手动构造 tool_calls
        async with client.messages.stream(**kwargs) as stream:
            async for chunk in stream:
                if chunk.type == "content_block_start":
                    if chunk.content_block.type == "tool_use":
                        if tool_calls is None:
                            tool_calls = []
                        tool_calls.append({
                            "id": chunk.content_block.id,
                            "function": {
                                "name": chunk.content_block.name,
                                "arguments": "",
                            },
                        })
                elif chunk.type == "content_block_delta":
                    if chunk.delta.type == "input_json_delta":
                        if tool_calls:
                            tool_calls[-1]["function"]["arguments"] += chunk.delta.partial_json

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


# ========== 便捷函数 ==========

async def stream_print(client: LLMClientV2, messages: list[dict], tools: list[dict] | None = None):
    """流式打印响应（带光标控制）"""
    import sys
    cursor = ""

    async for chunk in client.stream_chat(messages, tools):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
            cursor += chunk["content"]
        elif chunk["type"] == "done":
            print()  # 换行
            return {"content": chunk["content"], "tool_calls": chunk.get("tool_calls")}

    return {"content": cursor, "tool_calls": None}
