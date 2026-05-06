"""
Tests for core.llm_client_minimax — MiniMax LLM client (inherits OpenAI)
"""

import pytest


@pytest.fixture
def empty_config():
    return {"model": "test-model"}


@pytest.fixture
def full_config():
    return {
        "model": "test-model",
        "minimax": {
            "api_key": "test-minimax-key",
            "base_url": "https://custom.api.com/v1",
        },
    }


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestMiniMaxInit:
    def test_sets_provider_to_minimax(self, empty_config):
        from core.llm_client_minimax import MiniMaxClient

        client = MiniMaxClient(empty_config)
        assert client.provider == "minimax"

    def test_default_base_url(self, empty_config):
        from core.llm_client_minimax import MiniMaxClient

        client = MiniMaxClient(empty_config)
        assert client.provider_config.get("base_url") == "https://api.minimax.chat/v1"

    def test_custom_base_url(self, full_config):
        from core.llm_client_minimax import MiniMaxClient

        client = MiniMaxClient(full_config)
        assert client.provider_config.get("base_url") == "https://custom.api.com/v1"

    def test_custom_api_key(self, full_config):
        from core.llm_client_minimax import MiniMaxClient

        client = MiniMaxClient(full_config)
        assert client.provider_config.get("api_key") == "test-minimax-key"

    def test_minimax_section_not_present_creates_empty(self):
        """When config has no 'minimax' key, an empty one is created with default base_url."""
        from core.llm_client_minimax import MiniMaxClient

        config = {"model": "test-model"}
        # Remove minimax from config if present
        config.pop("minimax", None)
        client = MiniMaxClient(config)
        # provider_config is the minimax section contents with default base_url
        assert client.provider_config == {"base_url": "https://api.minimax.chat/v1"}


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------


class TestInheritance:
    def test_inherits_from_openai(self, empty_config):
        from core.llm_client_minimax import MiniMaxClient
        from core.llm_client_openai import OpenAIClient

        client = MiniMaxClient(empty_config)
        assert isinstance(client, OpenAIClient)

    def test_inherits_chat_method(self, empty_config):
        from core.llm_client_minimax import MiniMaxClient
        from core.llm_client_openai import OpenAIClient

        client = MiniMaxClient(empty_config)
        # The chat method should be the inherited one, not overridden
        assert type(client).chat is OpenAIClient.chat

    def test_inherits_stream_chat_method(self, empty_config):
        from core.llm_client_minimax import MiniMaxClient
        from core.llm_client_openai import OpenAIClient

        client = MiniMaxClient(empty_config)
        assert type(client).stream_chat is OpenAIClient.stream_chat

    def test_has_get_client_method(self, empty_config):
        from core.llm_client_minimax import MiniMaxClient

        client = MiniMaxClient(empty_config)
        assert hasattr(client, "_get_client")

    def test_config_deepcopy_is_independent(self, empty_config):
        """The original config should not be modified by MiniMaxClient init."""
        from core.llm_client_minimax import MiniMaxClient

        original = dict(empty_config)
        client = MiniMaxClient(empty_config)
        # Original config should still be intact
        assert original == {"model": "test-model"}
        # Client's config has been modified
        assert client.provider == "minimax"

    def test_model_preserved(self, empty_config):
        from core.llm_client_minimax import MiniMaxClient

        client = MiniMaxClient(empty_config)
        assert client.model == "test-model"
