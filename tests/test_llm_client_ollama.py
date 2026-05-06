"""
Tests for core.llm_client_ollama — Ollama LLM client
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.metrics import reset_metrics

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockAsyncIterable:
    """An async iterable from a list of values."""

    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for item in self._items:
            yield item


def make_response(content="", tool_calls=None):
    return {"message": {"content": content, "tool_calls": tool_calls}}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    return {
        "provider": "ollama",
        "model": "qwen3:4b",
        "ollama": {
            "host": "http://localhost:11434",
            "timeout": 30,
        },
    }


@pytest.fixture
def client(config):
    reset_metrics()
    from core.llm_client_ollama import OllamaClient

    return OllamaClient(config)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_sets_provider_and_model(self, config):
        from core.llm_client_ollama import OllamaClient

        c = OllamaClient(config)
        assert c.provider == "ollama"
        assert c.model == "qwen3:4b"

    def test_provider_config(self, config):
        from core.llm_client_ollama import OllamaClient

        c = OllamaClient(config)
        assert c.provider_config["host"] == "http://localhost:11434"


# ---------------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_creates_and_caches(self, client):
        with patch("ollama.AsyncClient") as mock_ollama:
            mock_instance = MagicMock()
            mock_ollama.return_value = mock_instance

            result1 = client._get_client()
            result2 = client._get_client()

            assert result1 is result2
            mock_ollama.assert_called_once()

    def test_passes_host(self, client):
        with patch("ollama.AsyncClient") as mock_ollama:
            client._get_client()
            mock_ollama.assert_called_once_with(host="http://localhost:11434")


# ---------------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------------


class TestChat:
    @pytest.mark.asyncio
    async def test_basic_chat(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat = AsyncMock(return_value=make_response(content="Hello from Ollama"))

            result = await client.chat([{"role": "user", "content": "hi"}])

            assert result["content"] == "Hello from Ollama"
            assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_chat_with_tools(self, client):
        tool_calls = [{"function": {"name": "get_weather", "arguments": '{"loc": "Beijing"}'}}]
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat = AsyncMock(return_value=make_response(content="", tool_calls=tool_calls))

            result = await client.chat(
                [{"role": "user", "content": "weather"}],
                tools=[{"function": {"name": "get_weather"}}],
            )

            assert result["content"] == ""
            assert result["tool_calls"] == tool_calls
            assert result["tool_calls"][0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_chat_empty_content(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat = AsyncMock(return_value=make_response(content="", tool_calls=None))

            result = await client.chat([{"role": "user", "content": ""}])

            assert result["content"] == ""
            assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_chat_network_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat = AsyncMock(side_effect=ConnectionError("ollama down"))

            with pytest.raises(ConnectionError, match="ollama down"):
                await client.chat([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_chat_timeout(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat = AsyncMock(side_effect=TimeoutError("timeout"))

            with pytest.raises(TimeoutError):
                await client.chat([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# stream_chat()
# ---------------------------------------------------------------------------


class TestStreamChat:
    @pytest.mark.asyncio
    async def test_streams_content(self, client):
        stream = MockAsyncIterable(
            [
                make_response(content="Hello"),
                make_response(content=" world"),
                make_response(content="!"),
            ]
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            # Note: stream_chat uses `async for response in client.chat(...)` without `await`,
            # so client.chat must return an async iterable directly (not a coroutine).
            mock_api.chat = MagicMock(return_value=stream)

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            # Total < 30 chars, so no intermediate flush. Text buffer flushed at end,
            # then done event.
            assert len(events) == 2
            assert events[0]["type"] == "content"
            assert events[0]["content"] == "Hello world!"
            assert events[1]["type"] == "done"
            assert events[1]["content"] == "Hello world!"
            assert events[1]["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_streams_content_with_buffer_flush(self, client):
        stream = MockAsyncIterable(
            [
                make_response(content="A" * 20),
                make_response(content="B" * 15),
                make_response(content="C" * 5),
            ]
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat = MagicMock(return_value=stream)

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            # Chunk 0: buffer=20 (<30), Chunk 1: buffer=35 (>=30) → content event
            # Chunk 2: buffer=5, end: flushed → content event
            # Then done event
            content_events = [e for e in events if e["type"] == "content"]
            assert len(content_events) == 2
            assert content_events[0]["content"] == "A" * 20 + "B" * 15
            assert content_events[1]["content"] == "C" * 5

            done_events = [e for e in events if e["type"] == "done"]
            assert len(done_events) == 1
            assert done_events[0]["content"] == "A" * 20 + "B" * 15 + "C" * 5

    @pytest.mark.asyncio
    async def test_streams_tool_calls(self, client):
        tool_call = {"function": {"name": "get_weather", "arguments": "{}"}}
        stream = MockAsyncIterable(
            [
                make_response(content="Let me check"),
                make_response(content="", tool_calls=[tool_call]),
            ]
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat = MagicMock(return_value=stream)

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            tool_call_events = [e for e in events if e["type"] == "tool_call"]
            assert len(tool_call_events) == 1
            assert tool_call_events[0]["tool_call"]["function"]["name"] == "get_weather"

            done_events = [e for e in events if e["type"] == "done"]
            assert done_events[0]["content"] == "Let me check"
            assert done_events[0]["tool_calls"] == [tool_call]

    @pytest.mark.asyncio
    async def test_stream_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat = MagicMock(side_effect=ConnectionError("stream failed"))

            with pytest.raises(ConnectionError):
                async for _ in client.stream_chat([{"role": "user", "content": "hi"}]):
                    pass
