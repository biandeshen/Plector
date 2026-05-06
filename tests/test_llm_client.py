"""
Tests for core.llm_client — Multi-backend LLM client factory/router
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    return {
        "provider": "ollama",
        "model": "qwen3:4b",
        "ollama": {"host": "http://localhost:11434"},
        "openai": {"api_key": "test-key", "base_url": "https://api.openai.com/v1"},
        "anthropic": {"api_key": "test-anthropic-key"},
    }


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_provider_and_model(self):
        from core.llm_client import LLMClient

        client = LLMClient({})
        assert client.provider == "ollama"
        assert client.model == "qwen3:4b"
        assert client.provider_config == {}

    def test_custom_config(self, config):
        from core.llm_client import LLMClient

        client = LLMClient(config)
        assert client.provider == "ollama"
        assert client.model == "qwen3:4b"
        assert client.provider_config == {"host": "http://localhost:11434"}


# ---------------------------------------------------------------------------
# _get_env
# ---------------------------------------------------------------------------


class TestGetEnv:
    def test_returns_plain_string(self):
        from core.llm_client import LLMClient

        client = LLMClient({})
        assert client._get_env("plain_value") == "plain_value"

    def test_resolves_env_var(self):
        from core.llm_client import LLMClient

        client = LLMClient({})
        with patch.dict(os.environ, {"MY_KEY": "resolved"}, clear=False):
            assert client._get_env("${MY_KEY}") == "resolved"

    def test_unset_env_var_raises(self):
        from core.llm_client import LLMClient

        client = LLMClient({})
        with patch.dict(os.environ, {}, clear=True), pytest.raises(ValueError, match="环境变量 MY_KEY 未设置"):
            client._get_env("${MY_KEY}")


# ---------------------------------------------------------------------------
# _convert_tools_for_anthropic
# ---------------------------------------------------------------------------


class TestConvertToolsForAnthropic:
    def test_converts_openai_format(self):
        from core.llm_client import LLMClient

        client = LLMClient({})
        tools = [
            {
                "function": {
                    "name": "get_weather",
                    "description": "Get weather info",
                    "parameters": {"type": "object", "properties": {}},
                }
            }
        ]
        result = client._convert_tools_for_anthropic(tools)
        assert result == [
            {
                "name": "get_weather",
                "description": "Get weather info",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]

    def test_multiple_tools(self):
        from core.llm_client import LLMClient

        client = LLMClient({})
        tools = [
            {
                "function": {
                    "name": "tool_a",
                    "description": "A",
                    "parameters": {"type": "object"},
                }
            },
            {
                "function": {
                    "name": "tool_b",
                    "description": "B",
                    "parameters": {"type": "object"},
                }
            },
        ]
        result = client._convert_tools_for_anthropic(tools)
        assert len(result) == 2
        assert result[0]["name"] == "tool_a"
        assert result[1]["name"] == "tool_b"


# ---------------------------------------------------------------------------
# chat() routing
# ---------------------------------------------------------------------------


class TestChatRouting:
    @pytest.fixture
    def messages(self):
        return [{"role": "user", "content": "hello"}]

    @pytest.mark.asyncio
    async def test_routes_to_ollama(self, messages):
        from core.llm_client import LLMClient

        client = LLMClient({"provider": "ollama", "ollama": {"host": "http://localhost:11434"}})
        with patch("ollama.AsyncClient") as mock_async_client_cls:
            mock_client = AsyncMock()
            mock_async_client_cls.return_value = mock_client
            mock_client.chat.return_value = {"message": {"content": "Hi!", "tool_calls": None}}

            result = await client.chat(messages)

            assert result["content"] == "Hi!"
            assert result["tool_calls"] is None
            mock_async_client_cls.assert_called_once_with(host="http://localhost:11434")

    @pytest.mark.asyncio
    async def test_routes_to_openai(self, messages):
        from core.llm_client import LLMClient

        client = LLMClient(
            {
                "provider": "openai",
                "openai": {
                    "api_key": "test-key",
                    "base_url": "https://api.openai.com/v1",
                },
            }
        )
        mock_msg = MagicMock(content="Hello from OpenAI", tool_calls=None)
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("openai.AsyncOpenAI") as mock_openai_cls:
            mock_instance = MagicMock()
            mock_openai_cls.return_value = mock_instance
            mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await client.chat(messages)

            assert result["content"] == "Hello from OpenAI"
            assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_routes_to_anthropic(self, messages):
        from core.llm_client import LLMClient

        client = LLMClient(
            {
                "provider": "anthropic",
                "anthropic": {"api_key": "test-anthropic-key"},
            }
        )
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Hello from Anthropic"
        mock_response = MagicMock()
        mock_response.content = [mock_block]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic_cls:
            mock_anthropic_client = AsyncMock()
            mock_anthropic_cls.return_value = mock_anthropic_client
            mock_anthropic_client.messages.create.return_value = mock_response

            result = await client.chat(messages)

            assert result["content"] == "Hello from Anthropic"
            assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_unsupported_provider_raises(self):
        from core.llm_client import LLMClient

        client = LLMClient({"provider": "unknown_provider"})
        with pytest.raises(ValueError, match="不支持的 provider"):
            await client.chat([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_ollama_with_tools(self, messages):
        from core.llm_client import LLMClient

        client = LLMClient({"provider": "ollama", "ollama": {"host": "http://localhost:11434"}})
        tools = [
            {
                "function": {
                    "name": "get_weather",
                    "description": "",
                    "parameters": {},
                }
            }
        ]

        with patch("ollama.AsyncClient") as mock_async_client_cls:
            mock_client = AsyncMock()
            mock_async_client_cls.return_value = mock_client
            mock_client.chat.return_value = {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_weather",
                                "arguments": "{}",
                            }
                        }
                    ],
                }
            }

            result = await client.chat(messages, tools)

            assert result["content"] == ""
            assert result["tool_calls"] is not None
            assert result["tool_calls"][0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_openai_with_tool_calls(self, messages):
        from core.llm_client import LLMClient

        client = LLMClient(
            {
                "provider": "openai",
                "openai": {
                    "api_key": "test-key",
                    "base_url": "https://api.openai.com/v1",
                },
            }
        )
        mock_tc = MagicMock()
        mock_tc.id = "call_1"
        mock_tc.function.name = "get_weather"
        mock_tc.function.arguments = '{"location": "Beijing"}'

        mock_msg = MagicMock(content="", tool_calls=[mock_tc])
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("openai.AsyncOpenAI") as mock_openai_cls:
            mock_instance = MagicMock()
            mock_openai_cls.return_value = mock_instance
            mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await client.chat(messages)
            assert result["content"] == ""
            assert result["tool_calls"] is not None
            assert result["tool_calls"][0]["id"] == "call_1"
            assert result["tool_calls"][0]["function"]["name"] == "get_weather"
