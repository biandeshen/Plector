import json
import os
import re
from collections.abc import AsyncIterator

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class LLMClient:
    """LLM 客户端抽象层，支持多后端"""

    def __init__(self, config: dict):
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model", "qwen3:4b")
        self.provider_config = config.get(self.provider, {})
        self._clients = {}  # 惰性初始化的客户端缓存

    def _get_ollama_client(self):
        """获取或创建 Ollama 客户端"""
        if "ollama" not in self._clients:
            import ollama
            self._clients["ollama"] = ollama.AsyncClient(
                host=self.provider_config.get("host", "http://localhost:11434")
            )
        return self._clients["ollama"]

    def _get_openai_client(self):
        """获取或创建 OpenAI 客户端"""
        if "openai" not in self._clients:
            from openai import AsyncOpenAI
            self._clients["openai"] = AsyncOpenAI(
                api_key=self._get_env(self.provider_config.get("api_key")),
                base_url=self.provider_config.get("base_url"),
            )
        return self._clients["openai"]

    def _get_anthropic_client(self):
        """获取或创建 Anthropic 客户端"""
        if "anthropic" not in self._clients:
            import anthropic
            self._clients["anthropic"] = anthropic.AsyncAnthropic(
                api_key=self._get_env(self.provider_config.get("api_key")),
            )
        return self._clients["anthropic"]

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """发送聊天请求，返回统一格式：{"content": str, "tool_calls": list or None}"""
        if self.provider == "ollama":
            return await self._ollama_chat(messages, tools)
        elif self.provider == "openai":
            return await self._openai_chat(messages, tools)
        elif self.provider == "anthropic":
            return await self._anthropic_chat(messages, tools)
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")

    async def stream_chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> AsyncIterator[dict]:
        """流式聊天，返回异步生成器"""
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

    async def _ollama_chat(self, messages, tools):
        """Ollama 后端"""
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
        """Ollama 流式请求"""
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
            delta = response.get("message", {})
            text = delta.get("content", "")
            if text:
                text = self._strip_thinking(text)
                content += text
                yield {"type": "content", "content": text}
            tcs = delta.get("tool_calls")
            if tcs:
                if tool_calls is None:
                    tool_calls = []
                for tc in tcs:
                    tc_item = {
                        "id": tc.get("id", f"call_{len(tool_calls)}"),
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", ""),
                        },
                    }
                    tool_calls.append(tc_item)
                    yield {"type": "tool_call", "tool_call": tc_item}
        yield {"type": "done", "content": content, "tool_calls": tool_calls}

    async def _openai_stream(self, messages, tools) -> AsyncIterator[dict]:
        """OpenAI 流式请求"""
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
        tool_buffer = {}  # index -> {id, name, arguments}

        async for response in await client.chat.completions.create(**kwargs):
            delta = response.choices[0].delta

            # 处理文本内容
            if delta.content:
                text = self._strip_thinking(delta.content)
                content += text
                yield {"type": "content", "content": text}

            # 处理 tool_calls 分片
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    index = tc_delta.index if hasattr(tc_delta, "index") else 0

                    # 初始化缓冲条目
                    if index not in tool_buffer:
                        func = tc_delta.function or {}
                        tool_buffer[index] = {
                            "id": tc_delta.id or f"call_{index}",
                            "name": func.name or "",
                            "arguments": "",
                        }
                        # 立即 yield tool_call_start
                        yield {"type": "tool_call", "tool_call": dict(tool_buffer[index])}

                    func = tc_delta.function or {}

                    # 合并 name
                    if func.name:
                        tool_buffer[index]["name"] = func.name

                    # 合并 arguments
                    if func.arguments:
                        tool_buffer[index]["arguments"] += func.arguments

                        # 尝试解析，如果成功则完成
                        try:
                            json.loads(tool_buffer[index]["arguments"])
                            completed = dict(tool_buffer[index])
                            del tool_buffer[index]
                            yield {"type": "tool_call_end", "tool_call": completed}
                        except json.JSONDecodeError:
                            pass

        # 处理残留缓冲
        for index, buf in tool_buffer.items():
            yield {"type": "tool_call_end", "tool_call": dict(buf)}

        yield {"type": "done", "content": content, "tool_calls": tool_calls}

    async def _openai_chat(self, messages, tools):
        """OpenAI 后端"""
        client = self._get_openai_client()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        response = await client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
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

    async def _anthropic_chat(self, messages, tools):
        """Anthropic 后端"""
        client = self._get_anthropic_client()
        # Anthropic 不支持 system 在 messages 里，需要单独传
        system_parts = []
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                user_messages.append(msg)

        system = "\n\n".join(system_parts) if system_parts else ""

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
        content = ""
        tool_calls = None
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
        return {
            "content": content,
            "tool_calls": tool_calls,
        }

    def _convert_tools_for_anthropic(self, tools):
        """将 OpenAI 格式的 tools 转换为 Anthropic 格式"""
        converted = []
        for tool in tools:
            converted.append(
                {
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"],
                }
            )
        return converted

    def _split_system(self, messages):
        """分离 system 和 user 消息"""
        system_parts = []
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                user_messages.append(msg)
        return ("\n\n".join(system_parts) if system_parts else "", user_messages)

    def _strip_thinking(self, text: str) -> str:
        """过滤掉 thinking tokens (<think>/</think>)"""
        while "<think>" in text and "</think>" in text:
            start = text.find("<think>")
            end = text.find("</think>")
            if end > start:
                text = text[:start] + text[end + len("</think>"):]
        return text.strip()

    async def _anthropic_stream(self, messages, tools) -> AsyncIterator[dict]:
        """Anthropic 流式请求"""
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
        with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        if tool_calls is None:
                            tool_calls = []
                        tool_calls.append({
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "arguments": "",
                        })
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        text = self._strip_thinking(event.delta.text)
                        content += text
                        yield {"type": "content", "content": text}
                    elif event.delta.type == "input_json_delta":
                        if tool_calls:
                            tool_calls[-1]["arguments"] += event.delta.partial_json
                elif event.type == "message_delta":
                    pass

        # 最终构建 tool_calls 列表
        final_tool_calls = None
        if tool_calls:
            final_tool_calls = [
                {
                    "id": tc["id"],
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                }
                for tc in tool_calls
            ]
        yield {"type": "done", "content": content, "tool_calls": final_tool_calls}

    def _get_env(self, value):
        """支持环境变量引用，如 ${OPENAI_API_KEY}"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            return os.environ.get(env_name, "")
        return value
