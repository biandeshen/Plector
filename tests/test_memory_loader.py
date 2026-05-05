from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.context_builder import ContextBuilder
from core.memory_loader import MemoryLoader


@pytest.fixture
def context_builder():
    return ContextBuilder(None)


@pytest.fixture
def loader(context_builder):
    return MemoryLoader(context_builder)


@pytest.mark.asyncio
async def test_load_empty_returns_empty_string(loader):
    with patch.object(loader, "_get_vm") as mock_vm_fn:
        mock_vm = Mock()
        mock_vm.search = AsyncMock(return_value=[])
        mock_vm_fn.return_value = mock_vm

        result = await loader.load("test_session")
        assert result == ""


@pytest.mark.asyncio
async def test_load_with_preferences(loader):
    prefs = [
        {"text": "prefers Python programming"},
        {"text": "likes concise code style"},
    ]
    with patch.object(loader, "_get_vm") as mock_vm_fn:
        mock_vm = Mock()
        mock_vm.search = AsyncMock(side_effect=[prefs, []])
        mock_vm_fn.return_value = mock_vm

        result = await loader.load("test_session")
        assert "## 用户偏好" in result
        assert "prefers Python programming" in result
        assert "likes concise code style" in result


@pytest.mark.asyncio
async def test_load_with_conversations(loader):
    long_text = "A" * 120
    convs = [
        {"text": long_text, "metadata": {"role": "user"}},
        {"text": "OK, let me explain the architecture.", "metadata": {"role": "assistant"}},
    ]
    with patch.object(loader, "_get_vm") as mock_vm_fn:
        mock_vm = Mock()
        mock_vm.search = AsyncMock(side_effect=[[], convs])
        mock_vm_fn.return_value = mock_vm

        result = await loader.load("test_session")
        assert "## 最近对话" in result
        assert "user:" in result
        assert "assistant:" in result
        assert "..." in result


@pytest.mark.asyncio
async def test_load_short_conversation_not_truncated(loader):
    convs = [
        {"text": "hello", "metadata": {"role": "user"}},
    ]
    with patch.object(loader, "_get_vm") as mock_vm_fn:
        mock_vm = Mock()
        mock_vm.search = AsyncMock(side_effect=[[], convs])
        mock_vm_fn.return_value = mock_vm

        result = await loader.load("test_session")
        assert "hello" in result


@pytest.mark.asyncio
async def test_load_exception_returns_empty(loader):
    with patch.object(loader, "_get_vm", side_effect=RuntimeError("ChromaDB connection failed")):
        result = await loader.load("test_session")
        assert result == ""


def test_build_system_prompt_without_memory(loader):
    loader.context_builder.build_system_prompt = Mock(return_value="base system prompt")
    result = loader.build_system_prompt("")
    assert result == "base system prompt"


def test_build_system_prompt_with_memory(loader):
    loader.context_builder.build_system_prompt = Mock(return_value="base system prompt")
    memory = "## 用户偏好\n- prefers Python"
    result = loader.build_system_prompt(memory)
    assert result.startswith("base system prompt")
    assert "## 用户偏好" in result
