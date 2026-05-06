"""
Tests for core.llm_client_openai — OpenAI-compatible LLM client
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.metrics import reset_metrics

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockAsyncStream:
    """Simulates OpenAI's async streaming response."""

    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for chunk in self._chunks:
            yield chunk


def make_delta(content=None, tool_calls=None):
    """Build a MagicMock delta object."""
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = tool_calls
    return delta


def make_chunk(delta_content=None, tool_calls=None):
    """Build a streaming chunk MagicMock."""
    delta = make_delta(content=delta_content, tool_calls=tool_calls)
    choice = MagicMock()
    choice.delta = delta
    chunk = MagicMock()
    chunk.choices = [choice]
    return chunk


def make_empty_choices_chunk():
    """Chunk with empty choices list — should be skipped."""
    chunk = MagicMock()
    chunk.choices = []
    return chunk


def make_tc(index=0, id_=None, name=None, arguments=None):
    """Build a ChoiceDeltaToolCall-like mock."""
    tc = MagicMock()
    tc.index = index
    tc.id = id_
    fn = MagicMock()
    fn.name = name
    fn.arguments = arguments
    tc.function = fn
    return tc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    return {
        "provider": "openai",
        "model": "gpt-4",
        "openai": {
            "api_key": "test-key",
            "base_url": "https://api.openai.com/v1",
            "timeout": 30,
        },
    }


@pytest.fixture
def client(config):
    reset_metrics()
    from core.llm_client_openai import OpenAIClient

    return OpenAIClient(config)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_sets_provider_and_model(self, config):
        from core.llm_client_openai import OpenAIClient

        c = OpenAIClient(config)
        assert c.provider == "openai"
        assert c.model == "gpt-4"

    def test_provider_config(self, config):
        from core.llm_client_openai import OpenAIClient

        c = OpenAIClient(config)
        assert c.provider_config["api_key"] == "test-key"
        assert c.provider_config["timeout"] == 30


# ---------------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_creates_and_caches_client(self, client):
        with patch("openai.AsyncOpenAI") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance

            result1 = client._get_client()
            result2 = client._get_client()

            assert result1 is result2
            mock_cls.assert_called_once()

    def test_passes_api_key_and_base_url(self, client):
        with patch("openai.AsyncOpenAI") as mock_cls:
            client._get_client()
            mock_cls.assert_called_once_with(api_key="test-key", base_url="https://api.openai.com/v1")


# ---------------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------------


class TestChat:
    @pytest.mark.asyncio
    async def test_basic_chat(self, client):
        mock_msg = MagicMock(content="Hello!", tool_calls=None)
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await client.chat([{"role": "user", "content": "hi"}])

            assert result["content"] == "Hello!"
            assert result["thinking"] == ""
            assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_chat_with_tools(self, client):
        mock_tc = MagicMock()
        mock_tc.id = "call_1"
        mock_tc.function.name = "get_weather"
        mock_tc.function.arguments = '{"loc": "Beijing"}'

        mock_msg = MagicMock(content="", tool_calls=[mock_tc])
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await client.chat(
                [{"role": "user", "content": "weather"}],
                tools=[{"function": {"name": "get_weather"}}],
            )

            assert result["content"] == ""
            assert result["tool_calls"] is not None
            assert len(result["tool_calls"]) == 1
            assert result["tool_calls"][0]["id"] == "call_1"
            assert result["tool_calls"][0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_chat_network_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(side_effect=ConnectionError("connection refused"))

            with pytest.raises(ConnectionError, match="connection refused"):
                await client.chat([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_chat_timeout(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(side_effect=TimeoutError("timeout"))

            with pytest.raises(TimeoutError):
                await client.chat([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# stream_chat()
# ---------------------------------------------------------------------------


class TestStreamChat:
    @pytest.mark.asyncio
    async def test_streams_content(self, client):
        chunks = [
            make_chunk(delta_content="Hello"),
            make_chunk(delta_content=" world"),
            make_chunk(delta_content="!"),
        ]
        stream = MockAsyncStream(chunks)

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(return_value=stream)

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            # Content is short (< 30 chars), so no intermediate flush events
            # The remaining text_buffer is flushed as a content event before done
            assert len(events) == 2
            assert events[0]["type"] == "content"
            assert events[0]["content"] == "Hello world!"
            assert events[1]["type"] == "done"
            assert events[1]["content"] == "Hello world!"
            assert events[1]["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_streams_content_with_buffer_flush(self, client):
        """When content accumulates >= 30 chars, intermediate yield happens."""
        chunks = [
            make_chunk(delta_content="A" * 25),
            make_chunk(delta_content="B" * 10),
            make_chunk(delta_content="C" * 5),
        ]
        stream = MockAsyncStream(chunks)

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(return_value=stream)

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            # After chunk 0: buffer = 25 chars (<30), no yield
            # After chunk 1: buffer = 35 chars (25+10), yield "A"*25+"B"*10, buffer cleared
            # After chunk 2: buffer = 5 chars, remains in buffer
            # End of stream: flush remaining 5 chars → content event
            # Then done event
            content_events = [e for e in events if e["type"] == "content"]
            assert len(content_events) == 2
            assert content_events[0]["content"] == "A" * 25 + "B" * 10
            assert content_events[1]["content"] == "C" * 5

            done_events = [e for e in events if e["type"] == "done"]
            assert len(done_events) == 1
            assert done_events[0]["content"] == "A" * 25 + "B" * 10 + "C" * 5

    @pytest.mark.asyncio
    async def test_streams_tool_calls(self, client):
        tc1 = make_tc(index=0, id_="call_1", name="get_weather")
        tc2 = make_tc(index=0, id_=None, name=None, arguments='{"loc": "Beijing"}')
        chunks = [
            make_chunk(tool_calls=[tc1]),
            make_chunk(tool_calls=[tc2]),
        ]
        stream = MockAsyncStream(chunks)

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(return_value=stream)

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            done_events = [e for e in events if e["type"] == "done"]
            assert len(done_events) == 1
            # tool_buffer should have one entry (index 0)
            assert done_events[0]["tool_calls"] is not None
            assert len(done_events[0]["tool_calls"]) == 1
            assert done_events[0]["tool_calls"][0]["id"] == "call_1"

    @pytest.mark.asyncio
    async def test_stream_skips_empty_choices(self, client):
        """Chunks with empty choices list are skipped entirely."""
        chunks = [
            make_chunk(delta_content="Hello"),
            make_empty_choices_chunk(),
            make_chunk(delta_content=" world"),
        ]
        stream = MockAsyncStream(chunks)

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(return_value=stream)

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            done_events = [e for e in events if e["type"] == "done"]
            assert done_events[0]["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_stream_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.chat.completions.create = AsyncMock(side_effect=ConnectionError("stream failed"))

            with pytest.raises(ConnectionError):
                async for _ in client.stream_chat([{"role": "user", "content": "hi"}]):
                    pass


# ---------------------------------------------------------------------------
# _normalize_message
# ---------------------------------------------------------------------------


class TestNormalizeMessage:
    def test_without_tool_calls(self, client):
        msg = MagicMock(content="Hello world", tool_calls=None)
        result = client._normalize_message(msg)
        assert result["content"] == "Hello world"
        assert result["thinking"] == ""
        assert result["tool_calls"] is None

    def test_with_tool_calls_string_arguments(self, client):
        """Arguments as a JSON string are kept as-is."""
        tc = MagicMock()
        tc.id = "call_1"
        tc.function.name = "get_weather"
        tc.function.arguments = '{"loc": "Beijing"}'

        msg = MagicMock(content="", tool_calls=[tc])
        result = client._normalize_message(msg)
        assert result["tool_calls"][0]["function"]["arguments"] == '{"loc": "Beijing"}'

    def test_with_tool_calls_dict_arguments(self, client):
        """Arguments as a dict are serialized to JSON."""
        tc = MagicMock()
        tc.id = "call_2"
        tc.function.name = "search"
        tc.function.arguments = {"q": "test"}

        msg = MagicMock(content="", tool_calls=[tc])
        result = client._normalize_message(msg)
        assert result["tool_calls"][0]["function"]["arguments"] == '{"q": "test"}'

    def test_multiple_tool_calls(self, client):
        tc1 = MagicMock()
        tc1.id = "call_1"
        tc1.function.name = "get_weather"
        tc1.function.arguments = "{}"

        tc2 = MagicMock()
        tc2.id = "call_2"
        tc2.function.name = "search"
        tc2.function.arguments = "{}"

        msg = MagicMock(content="", tool_calls=[tc1, tc2])
        result = client._normalize_message(msg)
        assert len(result["tool_calls"]) == 2


# ---------------------------------------------------------------------------
# _openai_append_tc
# ---------------------------------------------------------------------------


class TestOpenaiAppendTc:
    def test_creates_new_entry(self, client):
        tc = MagicMock()
        tc.index = 0
        tc.id = "call_0"
        tc.function.name = "get_weather"
        tc.function.arguments = ""

        tool_buffer = []
        emitted_indices = set()

        client._openai_append_tc(tc, 0, tool_buffer, emitted_indices)
        assert len(tool_buffer) == 1
        assert tool_buffer[0]["id"] == "call_0"
        assert tool_buffer[0]["function"]["name"] == "get_weather"

    def test_updates_existing_entry(self, client):
        tool_buffer = [
            {
                "id": "call_0",
                "function": {"name": "", "arguments": ""},
            }
        ]
        emitted_indices = set()

        tc = MagicMock()
        tc.index = 0
        tc.id = None
        tc.function.name = "search"
        tc.function.arguments = ""

        client._openai_append_tc(tc, 0, tool_buffer, emitted_indices)
        assert len(tool_buffer) == 1
        assert tool_buffer[0]["function"]["name"] == "search"

    def test_auto_generates_id_when_missing(self, client):
        tc = MagicMock()
        tc.index = 0
        tc.id = None
        tc.function.name = "test"
        tc.function.arguments = ""

        tool_buffer = []
        emitted_indices = set()
        client._openai_append_tc(tc, 0, tool_buffer, emitted_indices)

        assert tool_buffer[0]["id"] == "call_0"
        assert tool_buffer[0]["function"]["name"] == "test"

    def test_no_function_no_crash(self, client):
        """When tc.function is None, the method should not crash."""
        tc = MagicMock()
        tc.index = 0
        tc.id = "call_0"
        tc.function = None

        tool_buffer = []
        emitted_indices = set()
        # Should not raise
        client._openai_append_tc(tc, 0, tool_buffer, emitted_indices)
        assert len(tool_buffer) == 1
        assert tool_buffer[0]["function"]["name"] == ""
