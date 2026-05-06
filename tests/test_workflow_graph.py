"""
Tests for core.workflow_graph — LangGraph-based workflow engine.

LangGraph is not installed in the test environment, so all tests mock it.
"""

import json
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from core.workflow_graph import WorkflowEngine, WorkflowState

# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def mock_langgraph():
    """Mock LangGraph StateGraph and END symbols."""
    with patch("core.workflow_graph.StateGraph") as mock_sg_cls, patch("core.workflow_graph.END", "END"):
        mock_graph = MagicMock(name="graph")
        mock_sg_cls.return_value = mock_graph
        mock_compiled = AsyncMock(name="compiled")
        mock_graph.compile.return_value = mock_compiled
        yield mock_sg_cls, mock_graph, mock_compiled


@pytest.fixture
def engine():
    """WorkflowEngine with SkillRegistry / SkillHandler mocked out."""
    mock_registry = MagicMock()
    mock_handler = MagicMock()
    with (
        patch("core.workflow_graph.SkillRegistry", return_value=mock_registry),
        patch("core.workflow_graph.SkillHandler", return_value=mock_handler),
    ):
        yield WorkflowEngine({})


# ─── WorkflowState ─────────────────────────────────────────────────


class TestWorkflowState:
    """WorkflowState — default initialisation and history."""

    def test_defaults(self):
        state = WorkflowState()
        assert state["inputs"] == {}
        assert state["outputs"] == {}
        assert state["current_step"] == ""
        assert state["history"] == []
        assert state["error"] is None
        assert state["done"] is False

    def test_accepts_kwargs(self):
        state = WorkflowState(inputs={"x": 1}, done=True)
        assert state["inputs"] == {"x": 1}
        assert state["done"] is True
        assert state["outputs"] == {}  # default still set

    def test_add_history(self):
        state = WorkflowState()
        state.add_history("step_a", {"ok": True})
        assert len(state["history"]) == 1
        assert state["history"][0] == {"step": "step_a", "result": {"ok": True}}

    def test_add_history_multiple(self):
        state = WorkflowState()
        state.add_history("s1", 1)
        state.add_history("s2", 2)
        assert len(state["history"]) == 2


# ─── _build_graph ──────────────────────────────────────────────────


class TestBuildGraph:
    """_build_graph — node/edge/conditional routing construction."""

    def test_simple_linear(self, engine, mock_langgraph):
        _mock_sg_cls, mock_graph, _ = mock_langgraph
        workflow_def = {
            "entry": "start",
            "steps": [
                {"name": "start", "skill": "sk", "next": "END"},
            ],
        }
        result = engine._build_graph(workflow_def)
        assert result is mock_graph
        mock_graph.add_node.assert_called_once()
        mock_graph.add_edge.assert_called_once_with("start", "END")
        mock_graph.set_entry_point.assert_called_once_with("start")

    def test_multiple_steps(self, engine, mock_langgraph):
        _mock_sg_cls, mock_graph, _ = mock_langgraph
        workflow_def = {
            "steps": [
                {"name": "a", "skill": "sk1", "next": "b"},
                {"name": "b", "skill": "sk2", "next": "END"},
            ],
        }
        engine._build_graph(workflow_def)
        assert mock_graph.add_node.call_count == 2
        assert mock_graph.add_edge.call_count == 2
        mock_graph.set_entry_point.assert_called_once_with("a")

    def test_conditional_routing(self, engine, mock_langgraph):
        _mock_sg_cls, mock_graph, _ = mock_langgraph
        workflow_def = {
            "steps": [
                {
                    "name": "check",
                    "skill": "validator",
                    "next": {"conditions": {"success": "process", "failure": "END"}},
                },
                {"name": "process", "skill": "proc", "next": "END"},
            ],
        }
        engine._build_graph(workflow_def)
        # add_conditional_edges is called once per condition key
        assert mock_graph.add_conditional_edges.call_count == 2
        _, args, _ = mock_graph.add_conditional_edges.mock_calls[0]
        assert args[0] == "check"  # source node

    def test_node_without_skill_passes_lambda(self, engine, mock_langgraph):
        _mock_sg_cls, mock_graph, _ = mock_langgraph
        workflow_def = {
            "steps": [{"name": "passthrough", "next": "END"}],
        }
        engine._build_graph(workflow_def)
        mock_graph.add_node.assert_called_once()
        _name, func = mock_graph.add_node.call_args[0]
        assert callable(func)
        # Calling the lambda returns its input unchanged
        assert func(42) == 42

    def test_no_langgraph_returns_none(self):
        """When LangGraph is not installed _build_graph returns None."""
        with patch("core.workflow_graph.StateGraph", None):
            eng = WorkflowEngine({}, MagicMock())
            result = eng._build_graph({"steps": []})
            assert result is None

    def test_entry_point_defaults_to_first_step(self, engine, mock_langgraph):
        _mock_sg_cls, mock_graph, _ = mock_langgraph
        workflow_def = {
            "steps": [{"name": "first", "skill": "sk", "next": "END"}],
            # no explicit "entry"
        }
        engine._build_graph(workflow_def)
        mock_graph.set_entry_point.assert_called_once_with("first")


# ─── WorkflowEngine ────────────────────────────────────────────────


class TestWorkflowEngine:
    """run, run_from_yaml, resume, save_checkpoint."""

    @pytest.mark.asyncio
    async def test_run_success(self, engine, mock_langgraph):
        _, _, mock_compiled = mock_langgraph
        mock_compiled.ainvoke.return_value = {
            "outputs": {"step1": "ok"},
            "history": [{"step": "step1", "result": "ok"}],
            "error": None,
        }
        wf = {"steps": [{"name": "step1", "skill": "sk", "next": "END"}]}
        result = await engine.run(wf, {"x": 1})
        assert result["success"] is True
        assert result["result"] == {"step1": "ok"}

    @pytest.mark.asyncio
    async def test_run_returns_error_flag(self, engine, mock_langgraph):
        _, _, mock_compiled = mock_langgraph
        mock_compiled.ainvoke.return_value = {
            "outputs": {},
            "history": [],
            "error": "something broke",
        }
        result = await engine.run({"steps": []}, {})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_run_when_graph_is_none(self, engine):
        with patch.object(engine, "_build_graph", return_value=None):
            result = await engine.run({"steps": []}, {})
            assert result["success"] is False
            assert "图构建失败" in result["error"]

    @pytest.mark.asyncio
    async def test_run_catches_exception(self, engine):
        with patch.object(engine, "_build_graph", side_effect=ValueError("oops")):
            result = await engine.run({"steps": []}, {})
            assert result["success"] is False
            assert "oops" in result["error"]

    @pytest.mark.asyncio
    async def test_run_from_yaml(self, engine, mock_langgraph):
        _, _, mock_compiled = mock_langgraph
        mock_compiled.ainvoke.return_value = {"outputs": {}, "history": [], "error": None}
        yaml_text = "steps:\n  - name: t\n    skill: ts\n    next: END\n"
        with (
            patch("core.workflow_graph.PathManager.is_safe_path", return_value=True),
            patch("builtins.open", mock_open(read_data=yaml_text)),
        ):
            result = await engine.run_from_yaml("/fake/wf.yaml", {})
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_run_from_yaml_rejects_unsafe_path(self, engine):
        with patch("core.workflow_graph.PathManager.is_safe_path", return_value=False):
            result = await engine.run_from_yaml("/etc/evil.yaml", {})
            assert result["success"] is False
            assert "路径不在工作流目录内" in result["error"]

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, engine, mock_langgraph):
        _, _, mock_compiled = mock_langgraph
        mock_compiled.ainvoke.return_value = {"outputs": {"r": 1}, "history": [], "error": None}
        cp = json.dumps({"state": {"inputs": {}}, "workflow": {"steps": []}})
        with (
            patch("core.workflow_graph.PathManager.is_safe_path", return_value=True),
            patch("builtins.open", mock_open(read_data=cp)),
        ):
            result = await engine.resume("/fake/cp.json", {"extra": "x"})
            assert result["success"] is True
            assert result["result"] == {"r": 1}

    @pytest.mark.asyncio
    async def test_resume_rejects_unsafe_path(self, engine):
        with patch("core.workflow_graph.PathManager.is_safe_path", return_value=False):
            result = await engine.resume("/etc/bad.json", {})
            assert result["success"] is False
            assert "路径不在工作流目录内" in result["error"]

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, engine):
        state = WorkflowState(inputs={"k": "v"})
        wf = {"steps": []}
        m = mock_open()
        with patch("core.workflow_graph.PathManager.is_safe_path", return_value=True), patch("builtins.open", m):
            await engine.save_checkpoint(state, wf, "/fake/cp.json")
        handle = m()
        # Verify json content was written
        written_data = "".join(call[0][0] for call in handle.write.call_args_list)
        assert '"state"' in written_data
        assert '"workflow"' in written_data

    @pytest.mark.asyncio
    async def test_save_checkpoint_rejects_unsafe_path(self, engine):
        with (
            patch("core.workflow_graph.PathManager.is_safe_path", return_value=False),
            pytest.raises(ValueError, match="路径不在工作流目录内"),
        ):
            await engine.save_checkpoint(WorkflowState(), {}, "/etc/bad.json")

    def test_condition_function_routing(self, engine):
        """_create_condition returns correct keys based on output state."""
        cond_success = engine._create_condition("success", "next_ok")
        cond_failure = engine._create_condition("failure", "next_fail")
        cond_has_data = engine._create_condition("has_data", "next_data")

        # success condition — step output has success=True
        state1 = WorkflowState(current_step="s1", outputs={"s1": {"success": True}})
        assert cond_success(state1) == "success"

        state2 = WorkflowState(current_step="s1", outputs={"s1": {"success": False}})
        assert cond_success(state2) == "END"

        # failure condition
        state3 = WorkflowState(current_step="s1", outputs={"s1": {"success": False}})
        assert cond_failure(state3) == "failure"

        state4 = WorkflowState(current_step="s1", outputs={"s1": {"success": True}})
        assert cond_failure(state4) == "END"

        # has_data condition
        state5 = WorkflowState(current_step="s1", outputs={"s1": {"data": [1, 2]}})
        assert cond_has_data(state5) == "has_data"

        state6 = WorkflowState(current_step="s1", outputs={"s1": {}})
        assert cond_has_data(state6) == "END"

    def test_init_with_explicit_skill_handler(self):
        """Engine uses provided SkillHandler instead of creating one."""
        handler = MagicMock()
        eng = WorkflowEngine({"key": "val"}, handler)
        assert eng._skill_handler is handler
        assert eng._config == {"key": "val"}
