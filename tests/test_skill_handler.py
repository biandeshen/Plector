"""Tests for core.skill_handler — SkillHandler."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.skill_handler import SkillHandler

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def mock_registry():
    registry = MagicMock()
    registry.skills = {}
    return registry


@pytest.fixture
def handler(mock_registry):
    return SkillHandler(mock_registry)


# =========================================================================
# SkillHandler.__init__
# =========================================================================


class TestSkillHandlerInit:
    def test_stores_registry(self, handler, mock_registry):
        assert handler.registry is mock_registry


# =========================================================================
# SkillHandler.execute — missing skill
# =========================================================================


class TestSkillHandlerExecuteMissingSkill:
    @pytest.mark.asyncio
    async def test_returns_error_for_nonexistent_skill(self, handler):
        """get_skill returns None -> error dict returned."""
        handler.registry.get_skill.return_value = None
        result = await handler.execute("nonexistent", "test_method", {})
        assert "error" in result
        assert "不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_get_skill_called_with_correct_name(self, handler):
        handler.registry.get_skill.return_value = None
        await handler.execute("my_skill", "method", {})
        handler.registry.get_skill.assert_called_once_with("my_skill")


# =========================================================================
# SkillHandler.execute — module already loaded
# =========================================================================


class TestSkillHandlerExecuteModuleLoaded:
    @pytest.mark.asyncio
    async def test_calls_handler_method_when_module_already_loaded(self, handler):
        """When skill['module'] is not None, no import should happen."""
        mock_module = MagicMock()
        mock_handler_instance = MagicMock()
        mock_handler_instance.sync_method.return_value = "sync_result"

        mock_module.SkillHandler.return_value = mock_handler_instance

        skill_data = {
            "path": Path("/fake/skills/my_skill"),
            "meta": {"name": "my_skill"},
            "module": mock_module,
        }
        handler.registry.get_skill.return_value = skill_data

        result = await handler.execute("my_skill", "sync_method", {"arg": 1})

        assert result == {"result": "sync_result"}
        mock_handler_instance.sync_method.assert_called_once_with(arg=1)

    @pytest.mark.asyncio
    async def test_handles_async_method(self, handler):
        """When the handler method is a coroutine, it should be awaited."""
        mock_module = MagicMock()
        mock_handler_instance = MagicMock()

        async def async_method(**kwargs):
            return "async_result"

        mock_handler_instance.async_func = async_method
        mock_module.SkillHandler.return_value = mock_handler_instance

        skill_data = {
            "path": Path("/fake/skills/my_skill"),
            "meta": {"name": "my_skill"},
            "module": mock_module,
        }
        handler.registry.get_skill.return_value = skill_data

        result = await handler.execute("my_skill", "async_func", {"x": 2})

        assert result == {"result": "async_result"}


# =========================================================================
# SkillHandler.execute — module loading path
# =========================================================================


class TestSkillHandlerExecuteModuleLoading:
    @pytest.mark.asyncio
    async def test_loads_module_from_path(self, handler):
        """When skill['module'] is None, it should load from implementation.py."""

        class _FakeHandler:
            def do_work(self, **kwargs):
                return "called"

        skills_root = Path(__file__).resolve().parent.parent / "skills"
        skill_path = skills_root / "test_skill"

        skill_data = {
            "path": skill_path,
            "meta": {"name": "test_skill"},
            "module": None,
        }
        handler.registry.get_skill.return_value = skill_data

        fake_module = MagicMock()
        fake_module.SkillHandler = _FakeHandler

        with (
            patch("importlib.util.spec_from_file_location") as mock_spec_from,
            patch("importlib.util.module_from_spec") as mock_mod_from,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_spec = MagicMock()
            mock_spec_from.return_value = mock_spec
            mock_mod_from.return_value = fake_module

            result = await handler.execute("test_skill", "do_work", {"item": 1})

        assert result == {"result": "called"}
        mock_spec.loader.exec_module.assert_called_once_with(fake_module)

    @pytest.mark.asyncio
    async def test_raises_error_when_path_outside_skills_dir(self, handler):
        """Path traversal outside skills/ directory should raise ValueError."""
        skill_path = Path("/etc/passwd")

        skill_data = {
            "path": skill_path,
            "meta": {"name": "evil_skill"},
            "module": None,
        }
        handler.registry.get_skill.return_value = skill_data

        with pytest.raises(ValueError, match="超出 skills 目录范围"):
            await handler.execute("evil_skill", "method", {})


# =========================================================================
# SkillHandler.execute — missing class / method
# =========================================================================


class TestSkillHandlerExecuteMissingMembers:
    @pytest.mark.asyncio
    async def test_returns_error_when_no_skillhandler_class(self, handler):
        mock_module = MagicMock()
        # Remove SkillHandler attribute to simulate missing class
        mock_module.SkillHandler = None

        skill_data = {
            "path": Path("/fake/path"),
            "meta": {"name": "no_handler_skill"},
            "module": mock_module,
        }
        handler.registry.get_skill.return_value = skill_data

        result = await handler.execute("no_handler_skill", "method", {})
        assert "error" in result
        assert "没有 SkillHandler 类" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_when_method_missing(self, handler):
        """getattr for a nonexistent method should return None."""

        class _FakeHandler:
            pass

        mock_module = MagicMock()
        mock_module.SkillHandler = _FakeHandler

        skill_data = {
            "path": Path("/fake/path"),
            "meta": {"name": "partial_skill"},
            "module": mock_module,
        }
        handler.registry.get_skill.return_value = skill_data

        result = await handler.execute("partial_skill", "nonexistent_method", {})
        assert "error" in result
        assert "不存在" in result["error"]


# =========================================================================
# SkillHandler.execute — _mcp_call marker passthrough
# =========================================================================


class TestSkillHandlerMCPCallMarker:
    @pytest.mark.asyncio
    async def test_mcp_call_marker_preserved_in_output(self, handler):
        """The _mcp_call marker dict is returned as-is inside result."""
        mock_module = MagicMock()
        mock_handler_instance = MagicMock()

        mcp_result = {
            "_mcp_call": "agency-orchestrator",
            "tool": "run_workflow",
            "args": {"path": "/some/workflow.yaml"},
        }
        mock_handler_instance.delegate = MagicMock(return_value=mcp_result)
        mock_module.SkillHandler.return_value = mock_handler_instance

        skill_data = {
            "path": Path("/fake/path"),
            "meta": {"name": "orchestrator"},
            "module": mock_module,
        }
        handler.registry.get_skill.return_value = skill_data

        result = await handler.execute("orchestrator", "delegate", {"path": "/some/workflow.yaml"})

        assert "result" in result
        assert result["result"]["_mcp_call"] == "agency-orchestrator"
        assert result["result"]["tool"] == "run_workflow"

    @pytest.mark.asyncio
    async def test_mcp_call_marker_with_async_handler(self, handler):
        """Async handler returning _mcp_call marker should preserve it."""
        mock_module = MagicMock()
        mock_handler_instance = MagicMock()

        async def async_delegate(**kwargs):
            return {
                "_mcp_call": "agency-orchestrator",
                "tool": "validate_workflow",
                "args": {"path": kwargs.get("path")},
            }

        mock_handler_instance.async_delegate = async_delegate
        mock_module.SkillHandler.return_value = mock_handler_instance

        skill_data = {
            "path": Path("/fake/path"),
            "meta": {"name": "orchestrator"},
            "module": mock_module,
        }
        handler.registry.get_skill.return_value = skill_data

        result = await handler.execute("orchestrator", "async_delegate", {"path": "/test.yaml"})

        assert result["result"]["_mcp_call"] == "agency-orchestrator"
        assert result["result"]["tool"] == "validate_workflow"
        assert result["result"]["args"]["path"] == "/test.yaml"
