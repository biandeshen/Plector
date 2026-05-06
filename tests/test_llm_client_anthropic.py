"""
Tests for core.llm_client_anthropic — Anthropic LLM client
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.metrics import reset_metrics

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockAnthropicStream:
    """Simulates Anthropic's async streaming context manager."""

    def __init__(self, chunks):
        self._chunks = chunks

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for chunk in self._chunks:
            yield chunk


def make_text_block(text, type_="text"):
    block = MagicMock()
    block.type = type_
    block.text = text
    return block


def make_thinking_block(thinking):
    block = MagicMock()
    block.type = "thinking"
    block.thinking = thinking
    return block


def make_tool_use_block(name, input_, id_="toolu_abc123"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input_
    block.id = id_
    return block


def make_content_block_start_chunk(type_="text", **kwargs):
    chunk = MagicMock()
    chunk.type = "content_block_start"
    cb = MagicMock()
    cb.type = type_
    for k, v in kwargs.items():
        setattr(cb, k, v)
    chunk.content_block = cb
    return chunk


def make_text_delta_chunk(text):
    chunk = MagicMock()
    chunk.type = "content_block_delta"
    delta = MagicMock()
    delta.type = "text_delta"
    delta.text = text
    chunk.delta = delta
    return chunk


def make_input_json_delta_chunk(partial_json):
    chunk = MagicMock()
    chunk.type = "content_block_delta"
    delta = MagicMock()
    delta.type = "input_json_delta"
    delta.partial_json = partial_json
    chunk.delta = delta
    return chunk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    return {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "anthropic": {
            "api_key": "test-anthropic-key",
            "max_tokens": 4096,
            "timeout": 60,
        },
    }


@pytest.fixture
def client(config):
    reset_metrics()
    from core.llm_client_anthropic import AnthropicClient

    return AnthropicClient(config)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_sets_provider_and_model(self, config):
        from core.llm_client_anthropic import AnthropicClient

        c = AnthropicClient(config)
        assert c.provider == "anthropic"
        assert c.model == "claude-sonnet-4-20250514"

    def test_provider_config(self, config):
        from core.llm_client_anthropic import AnthropicClient

        c = AnthropicClient(config)
        assert c.provider_config["api_key"] == "test-anthropic-key"


# ---------------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_creates_and_caches(self, client):
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_cls = MagicMock()
            mock_anthropic.return_value = mock_cls

            result1 = client._get_client()
            result2 = client._get_client()

            assert result1 is result2
            mock_anthropic.assert_called_once()

    def test_passes_api_key(self, client):
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            client._get_client()
            mock_anthropic.assert_called_once_with(api_key="test-anthropic-key")


# ---------------------------------------------------------------------------
# chat()
# ---------------------------------------------------------------------------


class TestChat:
    @pytest.mark.asyncio
    async def test_basic_chat(self, client):
        mock_block = make_text_block("Hello from Claude")
        mock_response = MagicMock()
        mock_response.content = [mock_block]

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.messages.create = AsyncMock(return_value=mock_response)

            result = await client.chat([{"role": "user", "content": "hi"}])

            assert result["content"] == "Hello from Claude"
            assert result["thinking"] is None
            assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_chat_with_thinking(self, client):
        text_block = make_text_block("Final answer")
        think_block = make_thinking_block("Let me think...")
        mock_response = MagicMock()
        mock_response.content = [think_block, text_block]

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.messages.create = AsyncMock(return_value=mock_response)

            result = await client.chat([{"role": "user", "content": "think"}])

            assert result["content"] == "Final answer"
            assert result["thinking"] == "Let me think..."

    @pytest.mark.asyncio
    async def test_chat_with_tool_use(self, client):
        tool_block = make_tool_use_block("get_weather", {"loc": "Beijing"}, id_="toolu_1")
        mock_response = MagicMock()
        mock_response.content = [tool_block]

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.messages.create = AsyncMock(return_value=mock_response)

            result = await client.chat(
                [{"role": "user", "content": "weather"}],
                tools=[{"function": {"name": "get_weather", "description": "", "parameters": {}}}],
            )

            assert result["content"] == ""
            assert result["tool_calls"] is not None
            assert len(result["tool_calls"]) == 1
            assert result["tool_calls"][0]["id"] == "toolu_1"
            assert result["tool_calls"][0]["function"]["name"] == "get_weather"
            assert result["tool_calls"][0]["function"]["arguments"] == '{"loc": "Beijing"}'

    @pytest.mark.asyncio
    async def test_chat_network_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.messages.create = AsyncMock(side_effect=ConnectionError("API error"))

            with pytest.raises(ConnectionError):
                await client.chat([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_chat_with_system_message(self, client):
        """System message should be extracted and passed as kwargs."""
        text_block = make_text_block("Understood")
        mock_response = MagicMock()
        mock_response.content = [text_block]

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.messages.create = AsyncMock(return_value=mock_response)

            await client.chat(
                [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "ok"},
                ]
            )

            # Verify system was extracted and passed as kwarg
            call_kwargs = mock_api.messages.create.call_args.kwargs
            assert "system" in call_kwargs
            assert call_kwargs["system"] == "You are helpful"
            # User message should be in the messages list
            msgs = call_kwargs["messages"]
            assert len(msgs) == 1
            assert msgs[0]["role"] == "user"


# ---------------------------------------------------------------------------
# stream_chat()
# ---------------------------------------------------------------------------


class TestStreamChat:
    @pytest.mark.asyncio
    async def test_streams_text(self, client):
        """Basic text streaming."""
        stream = MockAnthropicStream(
            [
                make_text_delta_chunk("Hello"),
                make_text_delta_chunk(" world"),
            ]
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.messages.stream.return_value = stream

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            # Short text (< 30 chars): _process_chunk returns None (no flush),
            # so stream content stays empty. _emit_remaining flushes text_buffer
            # as a content event, but the done event's content is only populated
            # from _process_chunk events.
            content_events = [e for e in events if e["type"] == "content"]
            assert len(content_events) == 1
            assert content_events[0]["content"] == "Hello world"

            done_events = [e for e in events if e["type"] == "done"]
            assert len(done_events) == 1
            assert done_events[0]["content"] == ""

    @pytest.mark.asyncio
    async def test_streams_text_with_buffer_flush(self, client):
        """When buffer reaches threshold, intermediate content is yielded."""
        stream = MockAnthropicStream(
            [
                make_text_delta_chunk("A" * 20),
                make_text_delta_chunk("B" * 15),
                make_text_delta_chunk("C" * 5),
            ]
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.messages.stream.return_value = stream

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            # Chunk 0 (20): no flush. Chunk 1 (35 >=30): flush → content event.
            #   content variable updated to "A"*20+"B"*15.
            # Chunk 2 (5): no flush. End: _emit_remaining flushes "C"*5 → content event.
            #   content variable NOT updated from _emit_remaining.
            # Then done with content = "A"*20+"B"*15.
            content_events = [e for e in events if e["type"] == "content"]
            assert len(content_events) == 2
            assert content_events[0]["content"] == "A" * 20 + "B" * 15
            assert content_events[1]["content"] == "C" * 5

            done_events = [e for e in events if e["type"] == "done"]
            assert done_events[0]["content"] == "A" * 20 + "B" * 15

    @pytest.mark.asyncio
    async def test_streams_tool_calls(self, client):
        """Tool calls during streaming."""
        stream = MockAnthropicStream(
            [
                make_content_block_start_chunk("tool_use", name="get_weather", id="toolu_stream_1", input={}),
                make_input_json_delta_chunk('{"loc":'),
                make_input_json_delta_chunk(' "Beijing"}'),
            ]
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_api = MagicMock()
            mock_get.return_value = mock_api
            mock_api.messages.stream.return_value = stream

            events = []
            async for event in client.stream_chat([{"role": "user", "content": "hi"}]):
                events.append(event)

            done_events = [e for e in events if e["type"] == "done"]
            assert len(done_events) == 1
            assert done_events[0]["tool_calls"] is not None
            assert len(done_events[0]["tool_calls"]) == 1
            assert done_events[0]["tool_calls"][0]["id"] == "toolu_stream_1"
            assert done_events[0]["tool_calls"][0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_stream_error(self, client):
        mock_api = MagicMock()
        mock_api.messages.stream.side_effect = ConnectionError("stream failed")

        with patch.object(client, "_get_client") as mock_get:
            mock_get.return_value = mock_api

            with pytest.raises(ConnectionError):
                async for _ in client.stream_chat([{"role": "user", "content": "hi"}]):
                    pass


# ---------------------------------------------------------------------------
# _normalize_response
# ---------------------------------------------------------------------------


class TestNormalizeResponse:
    def test_text_only(self, client):
        response = MagicMock()
        response.content = [make_text_block("Hello")]
        result = client._normalize_response(response)
        assert result["content"] == "Hello"
        assert result["thinking"] is None
        assert result["tool_calls"] is None

    def test_thinking_block(self, client):
        response = MagicMock()
        response.content = [
            make_thinking_block("step by step"),
            make_text_block("Answer"),
        ]
        result = client._normalize_response(response)
        assert result["content"] == "Answer"
        assert result["thinking"] == "step by step"

    def test_tool_use(self, client):
        response = MagicMock()
        response.content = [make_tool_use_block("search", {"q": "test"}, id_="tu_1")]
        result = client._normalize_response(response)
        assert result["content"] == ""
        assert result["tool_calls"] is not None
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["id"] == "tu_1"
        assert result["tool_calls"][0]["function"]["name"] == "search"

    def test_mixed_content(self, client):
        response = MagicMock()
        response.content = [
            make_thinking_block("reasoning"),
            make_text_block("Final: "),
            make_tool_use_block("get_weather", {"loc": "Beijing"}, id_="tu_2"),
        ]
        result = client._normalize_response(response)
        assert result["content"] == "Final: "
        assert result["thinking"] == "reasoning"
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["id"] == "tu_2"


# ---------------------------------------------------------------------------
# _convert_tools
# ---------------------------------------------------------------------------


class TestConvertTools:
    def test_basic_conversion(self, client):
        tools = [
            {
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object"},
                }
            }
        ]
        result = client._convert_tools(tools)
        assert result == [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {"type": "object"},
            }
        ]


# ---------------------------------------------------------------------------
# _process_chunk
# ---------------------------------------------------------------------------


class TestProcessChunk:
    def test_text_delta(self, client):
        chunk = make_text_delta_chunk("Hello")
        text_buffer = []
        result = client._process_chunk(chunk, text_buffer, [], set())
        # Text is short (< 30), no output yet
        assert result is None
        assert text_buffer == ["Hello"]

    def test_text_delta_triggers_flush(self, client):
        chunk = make_text_delta_chunk("A" * 30)
        text_buffer = []
        result = client._process_chunk(chunk, text_buffer, [], set())
        assert result is not None
        assert result["type"] == "content"
        assert result["content"] == "A" * 30
        assert text_buffer == []

    def test_input_json_delta(self, client):
        chunk = make_input_json_delta_chunk('{"loc":')
        tool_buffer = [{"function": {"name": "search", "arguments": ""}}]
        emitted = set()
        result = client._process_chunk(chunk, [], tool_buffer, emitted)
        assert tool_buffer[0]["function"]["arguments"] == '{"loc":'
        # Not valid JSON yet, so no tool_call event
        assert result is None

    def test_input_json_delta_completes(self, client):
        chunk = make_input_json_delta_chunk('{"loc": "Beijing"}')
        tool_buffer = [{"function": {"name": "search", "arguments": ""}}]
        emitted = set()
        result = client._process_chunk(chunk, [], tool_buffer, emitted)

        assert tool_buffer[0]["function"]["arguments"] == '{"loc": "Beijing"}'
        assert result is not None
        assert result["type"] == "tool_call"

    def test_content_block_start_text_flushes_buffer(self, client):
        """Starting a new block flushes pending text buffer."""
        chunk = make_content_block_start_chunk("text", text="irrelevant")
        text_buffer = ["Hello"]
        result = client._process_chunk(chunk, text_buffer, [], set())
        assert result is not None
        assert result["type"] == "content"
        assert result["content"] == "Hello"
        assert text_buffer == []

    def test_content_block_start_tool_use(self, client):
        chunk = make_content_block_start_chunk("tool_use", name="search", id="tu_new")
        tool_buffer = []
        result = client._process_chunk(chunk, [], tool_buffer, set())
        assert result is None
        assert len(tool_buffer) == 1
        assert tool_buffer[0]["id"] == "tu_new"
        assert tool_buffer[0]["function"]["name"] == "search"

    def test_unknown_chunk_type(self, client):
        chunk = MagicMock()
        chunk.type = "unknown_type"
        result = client._process_chunk(chunk, [], [], set())
        assert result is None
