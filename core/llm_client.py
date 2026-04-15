import json
import os

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

    def _get_env(self, value):
        """支持环境变量引用，如 ${OPENAI_API_KEY}"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            return os.environ.get(env_name, "")
        return value
