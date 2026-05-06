import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tool_registry():
    """Fresh ToolRegistry instance for testing."""
    from core.function_calling import ToolRegistry

    return ToolRegistry()


@pytest.fixture
def basic_config():
    """Minimal config for AgentLoop construction in tests."""
    return {"llm": {"max_iterations": 5}}


@pytest.fixture
def mock_skill_registry():
    """SkillRegistry mock with empty skills dict."""
    registry = MagicMock()
    registry.skills = {}
    return registry


@pytest.fixture
def mock_llm_client():
    """LLMClient mock that returns a simple text response."""
    client = MagicMock()
    client.chat = AsyncMock(return_value={"content": "test response", "tool_calls": None})
    return client


@pytest.fixture
def agent_loop(basic_config):
    """AgentLoop with minimal config for testing."""
    from core.agent_loop import AgentLoop

    return AgentLoop(basic_config)
