from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.closure_engine import ClosureEngine


@pytest.fixture
def skill_handler():
    handler = MagicMock()
    handler.execute = AsyncMock()
    return handler


@pytest.fixture
def engine(skill_handler):
    with patch("builtins.open", MagicMock(side_effect=FileNotFoundError)):
        engine = ClosureEngine(skill_handler, config_path="config/closed_loops.yaml")
        engine.loops = {}
        return engine


# ─── Sanitize error ───────────────────────────────────────────


def test_sanitize_error_redacts_paths():
    msg = "File not found: C:\\Users\\dev\\data\\file.txt in operation"
    result = ClosureEngine._sanitize_error(msg)
    assert "C:\\Users" not in result
    assert "file.txt" in result


def test_sanitize_error_truncates_long_messages():
    msg = "x " * 250
    result = ClosureEngine._sanitize_error(msg)
    assert len(result) <= 203


def test_sanitize_error_preserves_short_no_path():
    msg = "Simple error message"
    result = ClosureEngine._sanitize_error(msg)
    assert result == msg


# ─── Skill node execution ────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_skill_node_success(engine):
    engine.skill_handler.execute.return_value = {"success": True, "data": "ok"}
    node = {"skill": "memory", "method": "save_knowledge", "next": "end", "params_from": "payload"}
    context = {"payload": {"topic": "test"}, "last_result": None}
    steps, errors = [], []

    next_node = await engine._execute_skill_node(node, "start", context, steps, errors)

    assert next_node == "end"
    assert len(steps) == 1
    assert steps[0]["success"] is True
    assert len(errors) == 0
    assert context["last_result"] == {"success": True, "data": "ok"}


@pytest.mark.asyncio
async def test_execute_skill_node_failure(engine):
    engine.skill_handler.execute.return_value = {"success": False, "error": "something broke"}
    node = {"skill": "error_knowledge", "method": "store_error", "params_from": "payload"}
    context = {"payload": {}, "last_result": None}
    steps, errors = [], []

    await engine._execute_skill_node(node, "error_node", context, steps, errors)

    assert steps[0]["success"] is False
    assert len(errors) == 1
    assert "something broke" in errors[0]["error"]


@pytest.mark.asyncio
async def test_execute_skill_node_uses_last_result(engine):
    engine.skill_handler.execute.return_value = {"success": True}
    node = {"skill": "memory", "method": "search_knowledge"}
    context = {"payload": {"ignored": True}, "last_result": {"query": "from_previous"}}

    await engine._execute_skill_node(node, "mid", context, [], [])

    call_kwargs = engine.skill_handler.execute.call_args[0][2]
    assert call_kwargs == {"query": "from_previous"}


# ─── Event subscription ──────────────────────────────────────


def test_create_handler_returns_coroutine(engine):
    engine.loops = {"test_loop": {"entry": "start", "nodes": {"start": {"type": "end"}}}}
    handler = engine._create_handler("test_loop")
    assert callable(handler)


# ─── Loop execution ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_loop_end_node(engine):
    engine.loops = {"simple": {"entry": "start", "max_iterations": 2, "nodes": {"start": {"type": "end"}}}}
    await engine._execute_loop(engine.loops["simple"], {"data": {"key": "val"}}, "simple")


@pytest.mark.asyncio
async def test_execute_loop_condition_node(engine):
    engine.skill_handler.execute.return_value = {"status": "ok"}
    engine.loops = {
        "cond_loop": {
            "entry": "check",
            "max_iterations": 3,
            "nodes": {
                "check": {
                    "type": "condition",
                    "transitions": {"ok": "action", "fail": "end"},
                },
                "action": {"type": "skill", "skill": "memory", "method": "check_health", "next": "end"},
                "end": {"type": "end"},
            },
        }
    }
    engine._execute_skill_node = AsyncMock(return_value="end")

    await engine._execute_loop(engine.loops["cond_loop"], {"data": {}}, "cond_loop")

    engine._execute_skill_node.assert_called_once()
