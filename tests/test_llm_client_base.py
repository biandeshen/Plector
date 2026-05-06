"""
Tests for core.llm_client_base
"""

import os
from unittest.mock import patch

import pytest

from core.llm_client_base import LLMClientBase
from core.metrics import reset_metrics


# Concrete subclass for testing the abstract base
class ConcreteClient(LLMClientBase):
    async def chat(self, messages, tools=None):
        return {"role": "assistant", "content": "test response"}

    async def stream_chat(self, messages, tools=None):
        yield {"role": "assistant", "content": "chunk"}


@pytest.fixture
def client():
    """Create a ConcreteClient with a minimal config."""
    return ConcreteClient({"provider": "test_provider", "model": "test_model", "test_provider": {"key": "val"}})


# ─── _get_env ────────────────────────────────────────────────────


class TestGetEnv:
    def test_returns_plain_string(self, client):
        """Plain string values are returned as-is."""
        assert client._get_env("plain_value") == "plain_value"

    def test_resolves_env_var(self, client):
        """${ENV_VAR} syntax resolves to the environment variable value."""
        with patch.dict(os.environ, {"MY_KEY": "resolved_value"}, clear=False):
            result = client._get_env("${MY_KEY}")
        assert result == "resolved_value"

    def test_empty_env_var_raises_value_error(self, client):
        """A ${VAR} reference to an unset variable raises ValueError."""
        with patch.dict(os.environ, {}, clear=True), pytest.raises(ValueError, match="环境变量 MY_KEY 未设置"):
            client._get_env("${MY_KEY}")

    def test_none_raises_value_error(self, client):
        """None value raises ValueError."""
        with pytest.raises(ValueError, match="API key / value 不能为空"):
            client._get_env(None)

    def test_empty_string_raises_value_error(self, client):
        """Empty string value raises ValueError."""
        with pytest.raises(ValueError, match="API key / value 不能为空"):
            client._get_env("")

    def test_env_var_is_empty_string_raises_value_error(self, client):
        """A ${VAR} reference where the env var exists but is empty raises ValueError."""
        with (
            patch.dict(os.environ, {"EMPTY_VAR": ""}, clear=False),
            pytest.raises(ValueError, match="环境变量 EMPTY_VAR 未设置"),
        ):
            client._get_env("${EMPTY_VAR}")

    def test_malformed_env_ref_treated_as_plain(self, client):
        """A string like ${VAR without closing brace is treated as a plain value."""
        assert client._get_env("${MY_KEY") == "${MY_KEY"


# ─── _split_system ──────────────────────────────────────────────


class TestSplitSystem:
    def test_no_system_messages(self, client):
        """No system messages returns empty string and all messages."""
        msgs = [{"role": "user", "content": "hello"}, {"role": "user", "content": "world"}]
        system, remaining = client._split_system(msgs)
        assert system == ""
        assert remaining == msgs

    def test_only_system_messages(self, client):
        """Only system messages returns joined content and empty list."""
        msgs = [{"role": "system", "content": "You are helpful."}, {"role": "system", "content": "Be concise."}]
        system, remaining = client._split_system(msgs)
        assert system == "You are helpful.\n\nBe concise."
        assert remaining == []

    def test_mixed_messages(self, client):
        """System messages are separated from user and assistant messages."""
        msgs = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "system", "content": "Another instruction"},
            {"role": "user", "content": "How are you?"},
        ]
        system, remaining = client._split_system(msgs)
        assert system == "System prompt\n\nAnother instruction"
        assert remaining == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ]

    def test_single_system_message(self, client):
        """A single system message is returned without extra newlines."""
        msgs = [{"role": "system", "content": "Just one."}, {"role": "user", "content": "ok"}]
        system, remaining = client._split_system(msgs)
        assert system == "Just one."
        assert len(remaining) == 1

    def test_empty_messages_list(self, client):
        """Empty message list returns empty string and empty list."""
        system, remaining = client._split_system([])
        assert system == ""
        assert remaining == []


# ─── _strip_thinking ────────────────────────────────────────────


class TestStripThinking:
    def test_no_thinking_content(self, client):
        """Text without thinking markers is returned unchanged."""
        text = "Hello, this is a normal response."
        filtered, thinking = client._strip_thinking(text)
        assert filtered == text
        assert thinking == ""

    def test_format1_double_wave(self, client):
        """﹏﹟...﹟﹏ style thinking is removed."""
        text = "Hello ﹏﹟thinking deeply﹟﹏ world."
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "Hello  world."
        assert "thinking deeply" in thinking

    def test_format1_multiple_double_wave(self, client):
        """Multiple ﹏﹟...﹟﹏ blocks are all stripped."""
        text = "A ﹏﹟think1﹟﹏ B ﹏﹟think2﹟﹏ C"
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "A  B  C"
        assert "think1" in thinking
        assert "think2" in thinking

    def test_format2_thinking_chinese_style(self, client):
        """【思考】...【/思考】 is removed."""
        text = "Answer.【思考】Let me reason about this.【/思考】 Final."
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "Answer. Final."
        assert "Let me reason about this" in thinking

    def test_format2_thinking_tag(self, client):
        """<thinking>...</thinking> is removed."""
        text = "Result. <thinking>step by step</thinking> Done."
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "Result.  Done."
        assert "step by step" in thinking

    def test_format2_think_tag(self, client):
        """<think>...</think> is removed."""
        text = "Output <think>internal reasoning</think> final."
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "Output  final."
        assert "internal reasoning" in thinking

    def test_format3_incomplete_double_wave(self, client):
        """Incomplete ﹏﹟ prefix without closing is also stripped."""
        text = "Here ﹏﹟partial thought"
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "Here"
        assert "partial thought" in thinking

    def test_format4_incomplete_think_open_tag(self, client):
        """<think> without closing tag at end is stripped."""
        text = "Result <think>unfinished reasoning"
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "Result"
        assert "unfinished reasoning" in thinking

    def test_incomplete_think_tag_not_at_end(self, client):
        """<think> without closing captures to end of string."""
        text = "A <think>partial more_text"
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "A"
        assert "partial more_text" in thinking

    def test_mixed_formats(self, client):
        """Multiple different thinking formats are all stripped."""
        text = "Start. ﹏﹟inner﹟﹏ middle. <think>reason</think> end."
        filtered, thinking = client._strip_thinking(text)
        assert "inner" not in filtered
        assert "reason" not in filtered
        assert filtered == "Start.  middle.  end."
        assert "inner" in thinking
        assert "reason" in thinking

    def test_think_tag_case_insensitive(self, client):
        """<THINK> (uppercase) is also matched."""
        text = "A <THINK>reasoning</THINK> B"
        filtered, thinking = client._strip_thinking(text)
        assert filtered == "A  B"
        assert "reasoning" in thinking

    def test_think_tag_mixed_case(self, client):
        """<Thinking> (mixed case) is also matched."""
        text = "A <Thinking>reason</Thinking> B"
        filtered, _thinking = client._strip_thinking(text)
        assert filtered == "A  B"

    def test_only_thinking_content(self, client):
        """When the entire text is thinking, filtered result is empty."""
        text = "<thinking>all thinking</thinking>"
        filtered, thinking = client._strip_thinking(text)
        assert filtered == ""
        assert "all thinking" in thinking

    def test_empty_string(self, client):
        """Empty string returns empty for both."""
        filtered, thinking = client._strip_thinking("")
        assert filtered == ""
        assert thinking == ""


# ─── _record_metrics ────────────────────────────────────────────


class TestRecordMetrics:
    @pytest.fixture(autouse=True)
    def _reset_global_metrics(self):
        reset_metrics()
        yield

    def test_records_llm_request(self, client):
        client._record_metrics(
            [{"role": "user", "content": "hello"}],
            duration=0.5,
        )
        from core.metrics import get_metrics_collector

        mc = get_metrics_collector()
        metrics = mc.get_all_metrics()
        assert metrics["llm"]["requests_total"] == 1
        assert metrics["llm"]["latency"]["count"] == 1
        assert metrics["llm"]["latency"]["avg"] == 0.5

    def test_records_tokens_from_content(self, client):
        """Token estimate is based on content length / 4."""
        # 100 chars → ~25 tokens
        client._record_metrics(
            [{"role": "system", "content": "x" * 100}],
            duration=0.1,
        )
        from core.metrics import get_metrics_collector

        mc = get_metrics_collector()
        assert mc.get_all_metrics()["llm"]["tokens_used_total"] == 25

    def test_multiple_messages_summed(self, client):
        """Token estimate sums over all messages."""
        client._record_metrics(
            [
                {"role": "system", "content": "a" * 40},
                {"role": "user", "content": "b" * 40},
            ],
            duration=0.2,
        )
        from core.metrics import get_metrics_collector

        mc = get_metrics_collector()
        # 80 chars / 4 = 20 tokens
        assert mc.get_all_metrics()["llm"]["tokens_used_total"] == 20

    def test_zero_content_does_not_record_tokens(self, client):
        """Messages with empty content do not increment tokens."""
        client._record_metrics(
            [{"role": "user", "content": ""}],
            duration=0.1,
        )
        from core.metrics import get_metrics_collector

        mc = get_metrics_collector()
        assert mc.get_all_metrics()["llm"]["tokens_used_total"] == 0

    def test_metrics_recorded_multiple_calls(self, client):
        """Consecutive calls to _record_metrics accumulate."""
        for i in range(3):
            client._record_metrics(
                [{"role": "user", "content": "hello"}],
                duration=float(i + 1),
            )
        from core.metrics import get_metrics_collector

        mc = get_metrics_collector()
        metrics = mc.get_all_metrics()
        assert metrics["llm"]["requests_total"] == 3
        assert metrics["llm"]["latency"]["count"] == 3
        # avg of 1, 2, 3 = 2.0
        assert metrics["llm"]["latency"]["avg"] == 2.0


# ─── __init__ ───────────────────────────────────────────────────


class TestInit:
    def test_config_stored(self, client):
        assert client.provider == "test_provider"
        assert client.model == "test_model"
        assert client.provider_config == {"key": "val"}

    def test_provider_config_empty_for_missing_section(self):
        """If the provider section isn't in config, provider_config is empty."""
        c = ConcreteClient({"provider": "unknown_provider", "model": "m"})
        assert c.provider_config == {}

    def test_clients_dict_initially_empty(self, client):
        assert client._clients == {}
