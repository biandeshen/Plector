"""
Tests for core/middleware_chain.py

Covers:
- MiddlewareContext get/set
- MiddlewareChain add/remove/execute
- GovernanceMiddleware, LoggingMiddleware, SecurityMiddleware
- MemoryMiddleware, AuditMiddleware
- Error handling in before/after callbacks
- Async handler execution
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from core.middleware_chain import (
    AuditMiddleware,
    GovernanceMiddleware,
    LoggingMiddleware,
    MemoryMiddleware,
    Middleware,
    MiddlewareChain,
    MiddlewareContext,
    SecurityMiddleware,
)

# ─── Helpers ─────────────────────────────────────────────


class FakeGovernance:
    """Minimal stand-in for core.governance.Governance."""

    def __init__(self):
        self.health_scores: dict[str, float] = {}
        self.eliminations: list[dict] = []

    def update_health_score(self, skill_name: str, success: bool, duration_ms: float) -> None:
        old = self.health_scores.get(skill_name, 1.0)
        success_factor = 1.0 if success else 0.0
        time_factor = max(0, 1 - (duration_ms / 10000))
        new = 0.7 * success_factor + 0.3 * time_factor
        self.health_scores[skill_name] = 0.9 * old + 0.1 * new


class FakeVectorMemory:
    """Minimal async stand-in for vector memory."""

    def __init__(self, results: list | None = None):
        self._results = results or []
        self.search_called_with: dict | None = None

    async def search(self, query: str, collection: str, n_results: int):
        self.search_called_with = {"query": query, "collection": collection, "n_results": n_results}
        return self._results


class CallRecorder(Middleware):
    """Records calls for verifying execution order."""

    name = "recorder"

    def __init__(self):
        self.calls = []

    async def before(self, ctx: MiddlewareContext) -> bool:
        self.calls.append(("before", ctx.session_id))
        return True

    async def after(self, ctx: MiddlewareContext, response: object) -> object:
        self.calls.append(("after", ctx.session_id))
        return response


# ─── MiddlewareContext ───────────────────────────────────


class TestMiddlewareContext:
    def test_defaults(self):
        ctx = MiddlewareContext()
        assert ctx.session_id == "default"
        assert ctx.user_input == ""
        assert ctx.messages == []
        assert ctx.metadata == {}

    def test_get_default(self):
        ctx = MiddlewareContext()
        assert ctx.get("nonexistent") is None
        assert ctx.get("nonexistent", 42) == 42

    def test_set_and_get(self):
        ctx = MiddlewareContext()
        ctx.set("key1", "value1")
        assert ctx.get("key1") == "value1"

    def test_set_overwrite(self):
        ctx = MiddlewareContext()
        ctx.set("key", "old")
        ctx.set("key", "new")
        assert ctx.get("key") == "new"

    def test_set_none_value(self):
        ctx = MiddlewareContext()
        ctx.set("key", None)
        assert ctx.get("key") is None

    def test_session_id_custom(self):
        ctx = MiddlewareContext(session_id="sess-001")
        assert ctx.session_id == "sess-001"

    def test_user_input_custom(self):
        ctx = MiddlewareContext(user_input="hello")
        assert ctx.user_input == "hello"

    def test_messages_custom(self):
        ctx = MiddlewareContext(messages=[{"role": "user", "content": "hi"}])
        assert len(ctx.messages) == 1

    def test_metadata_mutation(self):
        ctx = MiddlewareContext()
        ctx.metadata["a"] = 1
        assert ctx.get("a") == 1


# ─── MiddlewareChain ─────────────────────────────────────


class TestMiddlewareChain:
    def test_empty_chain_execute(self):
        chain = MiddlewareChain()
        ctx = MiddlewareContext(session_id="test")

        result = asyncio.run(chain.execute(ctx, lambda: "done"))

        assert result == "done"

    def test_add_and_remove(self):
        chain = MiddlewareChain()
        mw = CallRecorder()
        chain.add(mw)
        assert len(chain._middlewares) == 1
        chain.remove(mw)
        assert len(chain._middlewares) == 0

    def test_remove_nonexistent_no_error(self):
        chain = MiddlewareChain()
        mw = CallRecorder()
        chain.remove(mw)
        assert len(chain._middlewares) == 0

    def test_chainable_add(self):
        chain = MiddlewareChain()
        mw1 = CallRecorder()
        mw2 = CallRecorder()
        result = chain.add(mw1).add(mw2)
        assert result is chain
        assert len(chain._middlewares) == 2

    def test_execute_order(self):
        chain = MiddlewareChain()
        rec = CallRecorder()
        chain.add(rec)
        ctx = MiddlewareContext(session_id="s1")

        asyncio.run(chain.execute(ctx, lambda: "ok"))

        assert rec.calls == [("before", "s1"), ("after", "s1")]

    def test_async_handler(self):
        chain = MiddlewareChain()
        rec = CallRecorder()
        chain.add(rec)
        ctx = MiddlewareContext(session_id="s1")

        async def async_handler():
            return "async-result"

        result = asyncio.run(chain.execute(ctx, async_handler))

        assert result == "async-result"
        assert rec.calls == [("before", "s1"), ("after", "s1")]

    @pytest.mark.asyncio
    async def test_execute_returns_handler_result(self):
        chain = MiddlewareChain()
        ctx = MiddlewareContext()

        result = await chain.execute(ctx, lambda: 42)

        assert result == 42

    @pytest.mark.asyncio
    async def test_handler_can_raise_exception(self):
        chain = MiddlewareChain()
        ctx = MiddlewareContext()

        with pytest.raises(RuntimeError, match="handler failed"):
            await chain.execute(ctx, lambda: (_ for _ in ()).throw(RuntimeError("handler failed")))

    # ──  Error handling  ──────────────────────────────

    @pytest.mark.asyncio
    async def test_before_error_does_not_block_chain(self):
        """If before() raises an exception, the middleware is skipped but chain continues."""
        mw_err = CallRecorder()
        mw_err.before = AsyncMock(side_effect=ValueError("before error"))  # type: ignore[assignment]

        chain = MiddlewareChain()
        chain.add(mw_err)
        ctx = MiddlewareContext(session_id="s1")

        result = await chain.execute(ctx, lambda: "continues")

        assert result == "continues"

    @pytest.mark.asyncio
    async def test_handler_error_triggers_on_error(self):
        """When handler raises, on_error is called on all middlewares in reverse order."""
        errors = []

        class ErrorMiddleware(Middleware):
            name = "error_recorder"

            async def before(self, ctx: MiddlewareContext) -> bool:
                return True

            async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
                errors.append(str(error))

        chain = MiddlewareChain()
        mw = ErrorMiddleware()
        chain.add(mw)
        ctx = MiddlewareContext()

        with pytest.raises(RuntimeError, match="boom"):
            await chain.execute(ctx, lambda: (_ for _ in ()).throw(RuntimeError("boom")))

        assert len(errors) == 1
        assert "boom" in errors[0]

    @pytest.mark.asyncio
    async def test_on_error_itself_does_not_block_propagation(self):
        """If on_error raises, the original exception is still re-raised."""

        class BadOnErrorMiddleware(Middleware):
            name = "bad_on_error"

            async def before(self, ctx: MiddlewareContext) -> bool:
                return True

            async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
                raise ValueError("on_error itself failed")

        chain = MiddlewareChain()
        chain.add(BadOnErrorMiddleware())
        ctx = MiddlewareContext()

        with pytest.raises(RuntimeError, match="original"):
            await chain.execute(ctx, lambda: (_ for _ in ()).throw(RuntimeError("original")))

    @pytest.mark.asyncio
    async def test_after_error_does_not_block_response(self):
        """If after() raises, the response is still returned."""
        mw = CallRecorder()

        async def failing_after(ctx: MiddlewareContext, response: object) -> object:
            raise ValueError("after error")

        mw.after = failing_after  # type: ignore[assignment]

        chain = MiddlewareChain()
        chain.add(mw)
        ctx = MiddlewareContext()

        result = await chain.execute(ctx, lambda: "result-ok")

        assert result == "result-ok"

    @pytest.mark.asyncio
    async def test_multiple_middlewares_execute_in_order(self):
        chain = MiddlewareChain()
        order = []

        class OrderedMiddleware(Middleware):
            def __init__(self, mw_name: str):
                self.name = mw_name

            async def before(self, ctx: MiddlewareContext) -> bool:
                order.append(f"before_{self.name}")
                return True

            async def after(self, ctx: MiddlewareContext, response: object) -> object:
                order.append(f"after_{self.name}")
                return response

        chain.add(OrderedMiddleware("A")).add(OrderedMiddleware("B"))
        ctx = MiddlewareContext()

        await chain.execute(ctx, lambda: "done")

        assert order == ["before_A", "before_B", "after_A", "after_B"]

    @pytest.mark.asyncio
    async def test_all_after_runs_even_if_some_fail(self):
        """All middlewares get after() called even if one raises."""
        results = []

        chain = MiddlewareChain()

        class GoodAfter(Middleware):
            name = "good"

            async def before(self, ctx: MiddlewareContext) -> bool:
                return True

            async def after(self, ctx: MiddlewareContext, response: object) -> object:
                results.append("good_after")
                return response

        class BadAfter(Middleware):
            name = "bad"

            async def before(self, ctx: MiddlewareContext) -> bool:
                return True

            async def after(self, ctx: MiddlewareContext, response: object) -> object:
                raise ValueError("bad after")

        chain.add(GoodAfter()).add(BadAfter())
        ctx = MiddlewareContext()

        result = await chain.execute(ctx, lambda: "val")

        assert result == "val"
        assert "good_after" in results


# ─── GovernanceMiddleware ────────────────────────────────


class TestGovernanceMiddleware:
    @pytest.fixture
    def gov(self):
        g = FakeGovernance()
        g.health_scores["healthy_skill"] = 0.9
        g.health_scores["degraded_skill"] = 0.2
        return g

    @pytest.mark.asyncio
    async def test_no_skill_continues(self, gov):
        mw = GovernanceMiddleware(gov)
        ctx = MiddlewareContext()
        result = await mw.before(ctx)
        assert result is True

    @pytest.mark.asyncio
    async def test_healthy_skill_continues(self, gov):
        mw = GovernanceMiddleware(gov)
        ctx = MiddlewareContext()
        ctx.set("current_skill", "healthy_skill")
        result = await mw.before(ctx)
        assert result is True
        assert ctx.get("skill_degraded") is None

    @pytest.mark.asyncio
    async def test_degraded_skill_sets_context(self, gov):
        mw = GovernanceMiddleware(gov, min_health_score=0.3)
        ctx = MiddlewareContext()
        ctx.set("current_skill", "degraded_skill")  # score is 0.2
        result = await mw.before(ctx)
        assert result is True  # does not block, just flags
        assert ctx.get("skill_degraded") is True
        assert ctx.get("degraded_skill") == "degraded_skill"

    @pytest.mark.asyncio
    async def test_custom_min_health_score(self, gov):
        mw = GovernanceMiddleware(gov, min_health_score=0.5)
        ctx = MiddlewareContext()
        ctx.set("current_skill", "healthy_skill")  # 0.9
        await mw.before(ctx)
        assert ctx.get("skill_degraded") is None

        ctx2 = MiddlewareContext()
        ctx2.set("current_skill", "degraded_skill")  # 0.2
        await mw.before(ctx2)
        assert ctx2.get("skill_degraded") is True

    @pytest.mark.asyncio
    async def test_default_min_health_score_is_0_3(self):
        mw = GovernanceMiddleware(FakeGovernance())
        assert mw._min_health_score == 0.3

    @pytest.mark.asyncio
    async def test_on_error_updates_health(self, gov):
        mw = GovernanceMiddleware(gov)
        ctx = MiddlewareContext()
        ctx.set("current_skill", "healthy_skill")

        await mw.on_error(ctx, RuntimeError("fail"))

        assert gov.health_scores.get("healthy_skill", 1.0) < 0.9

    @pytest.mark.asyncio
    async def test_on_error_uses_degraded_skill_fallback(self, gov):
        """When current_skill is not set, fall back to degraded_skill."""
        mw = GovernanceMiddleware(gov)
        ctx = MiddlewareContext()
        ctx.set("degraded_skill", "degraded_skill")

        await mw.on_error(ctx, RuntimeError("fail"))

        assert gov.health_scores.get("degraded_skill", 1.0) < 1.0

    @pytest.mark.asyncio
    async def test_on_error_no_skill_no_crash(self):
        """If neither current_skill nor degraded_skill is set, on_error should not crash."""
        empty_gov = FakeGovernance()
        mw = GovernanceMiddleware(empty_gov)
        ctx = MiddlewareContext()

        await mw.on_error(ctx, RuntimeError("fail"))
        assert len(empty_gov.health_scores) == 0


# ─── LoggingMiddleware ──────────────────────────────────


class TestLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_before_logs_input(self, caplog):
        mw = LoggingMiddleware()
        ctx = MiddlewareContext(session_id="sess-001", user_input="hello world")

        with caplog.at_level(logging.INFO):
            result = await mw.before(ctx)

        assert result is True
        assert "sess-001" in caplog.text
        assert "hello world" in caplog.text

    @pytest.mark.asyncio
    async def test_after_logs_receipt(self, caplog):
        mw = LoggingMiddleware()
        ctx = MiddlewareContext(session_id="sess-001")

        with caplog.at_level(logging.INFO):
            result = await mw.after(ctx, "response-data")

        assert result == "response-data"
        assert "sess-001" in caplog.text
        assert "Response received" in caplog.text

    @pytest.mark.asyncio
    async def test_custom_log_level(self, caplog):
        mw = LoggingMiddleware(log_level="DEBUG")
        ctx = MiddlewareContext(session_id="s1", user_input="test")

        with caplog.at_level(logging.DEBUG):
            result = await mw.before(ctx)

        assert result is True
        assert "s1" in caplog.text

    @pytest.mark.asyncio
    async def test_before_truncates_long_input(self, caplog):
        long_input = "x" * 500
        mw = LoggingMiddleware()
        ctx = MiddlewareContext(session_id="s1", user_input=long_input)

        with caplog.at_level(logging.INFO):
            await mw.before(ctx)

        assert "x" * 100 in caplog.text
        assert "x" * 101 not in caplog.text

    @pytest.mark.asyncio
    async def test_after_passes_response_through(self):
        mw = LoggingMiddleware()
        ctx = MiddlewareContext()

        result = await mw.after(ctx, {"key": "value"})

        assert result == {"key": "value"}


# ─── SecurityMiddleware ─────────────────────────────────


class TestSecurityMiddleware:
    @pytest.mark.asyncio
    async def test_no_blocked_patterns_continues(self):
        mw = SecurityMiddleware()
        ctx = MiddlewareContext(user_input="safe input")
        result = await mw.before(ctx)
        assert result is True

    @pytest.mark.asyncio
    async def test_blocked_pattern_detected(self):
        mw = SecurityMiddleware(blocked_patterns=["<script>", "DROP TABLE"])
        ctx = MiddlewareContext(user_input="some <script> alert(1)")
        result = await mw.before(ctx)
        assert result is False
        assert ctx.get("blocked") is True
        assert "Pattern: <script>" in ctx.get("block_reason")

    @pytest.mark.asyncio
    async def test_case_insensitive_blocking(self):
        mw = SecurityMiddleware(blocked_patterns=["drop table"])
        ctx = MiddlewareContext(user_input="DROP TABLE users")
        result = await mw.before(ctx)
        assert result is False
        assert ctx.get("blocked") is True

    @pytest.mark.asyncio
    async def test_empty_blocked_patterns(self):
        mw = SecurityMiddleware(blocked_patterns=[])
        ctx = MiddlewareContext(user_input="anything")
        result = await mw.before(ctx)
        assert result is True

    @pytest.mark.asyncio
    async def test_multiple_patterns_first_match_wins(self):
        mw = SecurityMiddleware(blocked_patterns=["hack", "exploit", "drop"])
        ctx = MiddlewareContext(user_input="run DROP TABLE")
        result = await mw.before(ctx)
        assert result is False
        assert "drop" in ctx.get("block_reason")


# ─── MemoryMiddleware ───────────────────────────────────


class TestMemoryMiddleware:
    @pytest.mark.asyncio
    async def test_no_vector_memory_skips(self):
        mw = MemoryMiddleware(vector_memory=None)
        ctx = MiddlewareContext(user_input="hello")
        result = await mw.before(ctx)
        assert result is True
        assert ctx.get("memory_context") is None

    @pytest.mark.asyncio
    async def test_with_vector_memory_sets_context(self):
        vm = FakeVectorMemory(results=[{"id": 1, "text": "pref"}])
        mw = MemoryMiddleware(vector_memory=vm)
        ctx = MiddlewareContext(user_input="preferences please")
        result = await mw.before(ctx)
        assert result is True
        assert ctx.get("memory_context") == [{"id": 1, "text": "pref"}]

    @pytest.mark.asyncio
    async def test_search_called_with_correct_params(self):
        vm = FakeVectorMemory(results=[])
        mw = MemoryMiddleware(vector_memory=vm)
        ctx = MiddlewareContext(user_input="my query")
        await mw.before(ctx)
        assert vm.search_called_with == {
            "query": "my query",
            "collection": "preferences",
            "n_results": 5,
        }

    @pytest.mark.asyncio
    async def test_search_error_does_not_block(self):
        vm = FakeVectorMemory(results=[])

        async def broken_search(query: str, collection: str, n_results: int):
            raise RuntimeError("search failed")

        vm.search = broken_search  # type: ignore[assignment]
        mw = MemoryMiddleware(vector_memory=vm)
        ctx = MiddlewareContext(user_input="test")

        result = await mw.before(ctx)
        assert result is True
        assert ctx.get("memory_context") is None


# ─── AuditMiddleware ────────────────────────────────────


class TestAuditMiddleware:
    @pytest.mark.asyncio
    async def test_writes_audit_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            mw = AuditMiddleware(audit_log_path=str(log_path))
            ctx = MiddlewareContext(session_id="sess-001", user_input="test input")

            result = await mw.after(ctx, "response")

            assert result == "response"
            assert log_path.exists()
            content = log_path.read_text(encoding="utf-8")
            entry = json.loads(content.strip())
            assert entry["session_id"] == "sess-001"
            assert entry["user_input"] == "test input"
            assert "timestamp" in entry

    @pytest.mark.asyncio
    async def test_truncates_long_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            mw = AuditMiddleware(audit_log_path=str(log_path))
            long_input = "x" * 500
            ctx = MiddlewareContext(session_id="s1", user_input=long_input)

            await mw.after(ctx, "resp")

            content = log_path.read_text(encoding="utf-8")
            entry = json.loads(content.strip())
            assert len(entry["user_input"]) == 200

    @pytest.mark.asyncio
    async def test_passes_response_through(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            mw = AuditMiddleware(audit_log_path=str(log_path))
            ctx = MiddlewareContext()

            result = await mw.after(ctx, {"original": "data"})

            assert result == {"original": "data"}

    @pytest.mark.asyncio
    async def test_write_error_does_not_block(self):
        """If audit log writing fails, after() still returns the response."""
        mw = AuditMiddleware(audit_log_path="/nonexistent_dir/audit.log")
        ctx = MiddlewareContext()

        result = await mw.after(ctx, "data")
        assert result == "data"

    @pytest.mark.asyncio
    async def test_default_log_path(self):
        mw = AuditMiddleware()
        assert mw._log_path == "logs/audit.log"


# ─── MiddlewareChain end-to-end integration ──────────────


class TestMiddlewareChainIntegration:
    @pytest.mark.asyncio
    async def test_full_chain_with_all_middlewares(self):
        """Execute with all concrete middlewares together."""
        gov = FakeGovernance()
        gov.health_scores["test_skill"] = 0.9

        chain = MiddlewareChain()
        chain.add(LoggingMiddleware())
        chain.add(SecurityMiddleware(blocked_patterns=["evil"]))
        chain.add(GovernanceMiddleware(gov))

        ctx = MiddlewareContext(session_id="integ", user_input="hello skill")
        ctx.set("current_skill", "test_skill")

        result = await chain.execute(ctx, lambda: "success")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_security_blocks_in_chain(self):
        """When SecurityMiddleware.before returns False, chain continues but marks skip."""
        chain = MiddlewareChain()
        chain.add(SecurityMiddleware(blocked_patterns=["evil"]))

        ctx = MiddlewareContext(session_id="sec-test", user_input="evil input")

        result = await chain.execute(ctx, lambda: "still runs")

        assert result == "still runs"
        assert ctx.get("blocked") is True
