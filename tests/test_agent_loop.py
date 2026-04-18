"""
Unit tests for core/agent_loop.py
"""
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from core.agent_loop import AgentLoop, filter_think_tags


class TestFilterThinkTags:
    """Tests for filter_think_tags() function"""

    def test_standard_format(self):
        """Test standard format: ﹏﹟content﹟"""
        content = "Hello ﹏﹟thinking content﹟ World"
        result = filter_think_tags(content)
        assert "thinking content" not in result
        assert "Hello" in result
        assert "World" in result

    def test_only_opening_tag(self):
        """Test only opening tag: ﹏﹟content without closing"""
        content = "Hello ﹏﹟incomplete thought"
        result = filter_think_tags(content)
        assert "incomplete thought" not in result
        assert "Hello" in result

    def test_only_closing_tag(self):
        """Test only closing tag: content﹟ - removes only the tag, not preceding text"""
        content = "Start content﹟ End"
        result = filter_think_tags(content)
        # Closing tag alone only removes the ﹟ character
        assert "Start" in result
        assert "End" in result
        # The closing tag ﹟ is removed
        assert "﹟" not in result

    def test_multiple_tags(self):
        """Test multiple tags in content"""
        content = "﹏﹟think1﹟ A ﹏﹟think2﹟ B ﹟ C"
        result = filter_think_tags(content)
        assert "think1" not in result
        assert "think2" not in result
        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_no_tags_plain_text(self):
        """Test plain text without any tags"""
        content = "This is plain text without any tags"
        result = filter_think_tags(content)
        assert result == content

    def test_empty_string(self):
        """Test empty string"""
        result = filter_think_tags("")
        assert result == ""

    def test_none_input(self):
        """Test None input returns None"""
        result = filter_think_tags(None)
        assert result is None

    def test_multiple_newlines_cleaned(self):
        """Test multiple newlines are cleaned to double newlines"""
        content = "Line1\n\n\n\nLine2"
        result = filter_think_tags(content)
        assert "\n\n\n" not in result
        assert result == "Line1\n\nLine2"

    def test_think_tag_complete(self):
        """Test standard <think>...</think> tag filtering"""
        content = "Hello <think>let me think about this</think> World"
        result = filter_think_tags(content)
        assert "let me think" not in result
        assert "Hello" in result
        assert "World" in result

    def test_think_tag_incomplete_open(self):
        """Test incomplete <think> tag (no closing) - simulates streaming chunk"""
        content = "Hello <think>still thinking..."
        result = filter_think_tags(content)
        assert "still thinking" not in result
        assert "<think>" not in result
        assert "Hello" in result

    def test_think_tag_orphan_close(self):
        """Test orphan </think> closing tag"""
        content = "some content</think> World"
        result = filter_think_tags(content)
        assert "</think>" not in result
        assert "World" in result

    def test_thinking_tag_complete(self):
        """Test <thinking>...</thinking> tag filtering"""
        content = "Start <thinking>deep thought</thinking> End"
        result = filter_think_tags(content)
        assert "deep thought" not in result
        assert "Start" in result
        assert "End" in result

    def test_thinking_tag_incomplete(self):
        """Test incomplete <thinking> tag"""
        content = "Hello <thinking>partial thought"
        result = filter_think_tags(content)
        assert "partial thought" not in result
        assert "Hello" in result

    def test_cross_chunk_simulation(self):
        """Simulate cross-chunk <think> tag by accumulating chunks"""
        # chunk1 has incomplete tag, chunk2 completes it
        chunk1 = "Answer: <thi"
        chunk2 = "nk>secret reasoning</think> The result is 42"
        accumulated = chunk1 + chunk2
        result = filter_think_tags(accumulated)
        assert "secret reasoning" not in result
        assert "<think>" not in result
        assert "The result is 42" in result

    def test_mixed_formats(self):
        """Test mixed think tag formats in one content"""
        content = "<think>thought1</think> A ﹏﹟thought2﹟ B <thinking>thought3</thinking> C"
        result = filter_think_tags(content)
        assert "thought1" not in result
        assert "thought2" not in result
        assert "thought3" not in result
        assert "A" in result
        assert "B" in result
        assert "C" in result


class TestSaveConversationSync:
    """Tests for _save_conversation_sync()"""

    def test_save_conversation_with_mocked_sqlite3(self):
        """Test saving conversation with mocked sqlite3"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("sqlite3.connect", return_value=mock_conn) as mock_connect, \
             patch("core.agent_loop.os.environ.get", return_value=":memory:"):
                agent = AgentLoop.__new__(AgentLoop)
                agent._save_conversation_sync("session_123", "user", "Hello")

                mock_connect.assert_called_once_with(":memory:")
                mock_cursor.execute.assert_called_once()
                mock_conn.commit.assert_called_once()
                mock_conn.close.assert_called_once()

    def test_save_conversation_handles_exception(self):
        """Test exception handling in _save_conversation_sync"""
        with patch("sqlite3.connect", side_effect=sqlite3.Error("DB error")), \
             patch("core.agent_loop.logger") as mock_logger:
                agent = AgentLoop.__new__(AgentLoop)
                agent._save_conversation_sync("session_123", "user", "Hello")
                mock_logger.warning.assert_called_once()


class TestRegisterSkillsAsTools:
    """Tests for _register_skills_as_tools()"""

    def test_register_skills_as_tools(self):
        """Test that skills are registered as tools"""
        mock_registry = MagicMock()
        mock_registry.skills = {
            "test_skill": {
                "meta": {
                    "tools": [
                        {
                            "name": "test_tool",
                            "description": "A test tool",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"arg": {"type": "string"}},
                                "required": ["arg"],
                                "additionalProperties": False,
                            },
                        }
                    ]
                }
            }
        }

        with patch.object(AgentLoop, "__init__", lambda x, y=None: None):
            agent = AgentLoop()
            agent.skill_registry = mock_registry
            agent.tool_registry = MagicMock()
            agent.closure_engine = MagicMock()
            agent.skill_handler = MagicMock()

            agent._register_skills_as_tools()

            agent.tool_registry.register.assert_called_once()
            call_args = agent.tool_registry.register.call_args
            assert call_args.kwargs["name"] == "test_skill_test_tool"
            assert call_args.kwargs["description"] == "A test tool"

    def test_multiple_tools_registered(self):
        """Test multiple tools from multiple skills are registered"""
        mock_registry = MagicMock()
        mock_registry.skills = {
            "skill_a": {"meta": {"tools": [{"name": "tool_a1"}, {"name": "tool_a2"}]}},
            "skill_b": {"meta": {"tools": [{"name": "tool_b1"}]}},
        }

        with patch.object(AgentLoop, "__init__", lambda x, y=None: None):
            agent = AgentLoop()
            agent.skill_registry = mock_registry
            agent.tool_registry = MagicMock()
            agent.closure_engine = MagicMock()
            agent.skill_handler = MagicMock()

            agent._register_skills_as_tools()

            assert agent.tool_registry.register.call_count == 3


class TestAgentLoopAsync:
    """Async tests for AgentLoop"""

    @pytest.mark.asyncio
    async def test_save_conversation_async(self):
        """Test async save conversation"""
        with patch.object(AgentLoop, "_save_conversation_sync") as mock_sync, \
             patch.object(AgentLoop, "__init__", lambda x, y=None: None):
                agent = AgentLoop()
                agent._save_conversation_sync = mock_sync

                await agent._save_conversation("session_1", "user", "Hello")

                mock_sync.assert_called_once_with("session_1", "user", "Hello")

    @pytest.mark.asyncio
    async def test_handle_image_command_returns_none_for_regular_input(self):
        """Test _handle_image_command returns None for non-image commands"""
        with patch.object(AgentLoop, "__init__", lambda x, y=None: None):
            agent = AgentLoop()
            agent.skill_handler = MagicMock()

            result = await agent._handle_image_command("regular user input")
            assert result is None

    def test_build_assistant_message(self):
        """Test _build_assistant_message creates correct structure"""
        with patch.object(AgentLoop, "__init__", lambda x, y=None: None):
            agent = AgentLoop()
            full_response = "Test response"
            tool_calls_buffer = [
                {
                    "id": "call_1",
                    "function": {"name": "test_tool", "arguments": '{"arg": "value"}'},
                }
            ]

            result = agent._build_assistant_message(full_response, tool_calls_buffer)

            assert result["role"] == "assistant"
            assert result["content"] == full_response
            assert len(result["tool_calls"]) == 1
            assert result["tool_calls"][0]["function"]["name"] == "test_tool"
