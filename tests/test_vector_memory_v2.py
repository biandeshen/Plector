"""
Tests for core.vector_memory_v2 — enhanced vector memory with caching, batch ops, decay.

Inherits from VectorMemory, so we mock the parent __init__ to skip ChromaDB.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.vector_memory_v2 import (
    CacheEntry,
    MemoryIntensity,
    VectorMemoryV2,
)

# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def v2():
    """VectorMemoryV2 with parent __init__ mocked and mock collections attached."""
    with patch("core.vector_memory.VectorMemory.__init__", return_value=None):
        vm = VectorMemoryV2({"cache_enabled": True, "cache_ttl": 60, "cache_max_size": 5})
        vm.conversations = MagicMock(name="conversations")
        vm.knowledge = MagicMock(name="knowledge")
        vm.preferences = MagicMock(name="preferences")
        vm.context_saver = MagicMock(name="context_saver")
        yield vm


# ─── Initialisation ────────────────────────────────────────────────


class TestInit:
    def test_config_defaults(self):
        """When config is empty / None, default cache settings apply."""
        with patch("core.vector_memory.VectorMemory.__init__", return_value=None):
            vm = VectorMemoryV2({})
            assert vm._cache_enabled is True
            assert vm._cache_ttl == 300
            assert vm._cache_max_size == 1000

            vm2 = VectorMemoryV2()
            assert vm2._cache_enabled is True

    def test_custom_config(self):
        with patch("core.vector_memory.VectorMemory.__init__", return_value=None):
            vm = VectorMemoryV2({"cache_enabled": False, "cache_ttl": 10, "cache_max_size": 3})
            assert vm._cache_enabled is False
            assert vm._cache_ttl == 10
            assert vm._cache_max_size == 3

    def test_empty_cache_on_init(self, v2):
        assert v2._query_cache == {}
        assert v2._cache_hits == 0
        assert v2._cache_misses == 0


# ─── add_batch ─────────────────────────────────────────────────────


class TestAddBatch:
    @pytest.mark.asyncio
    async def test_empty_items(self, v2):
        result = await v2.add_batch([])
        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_batch_all_success(self, v2):
        v2.add = AsyncMock(return_value={"success": True})  # type: ignore[assignment]
        items = [("hello", {"k": "v"}), ("world", {"k2": "v2"})]
        result = await v2.add_batch(items)
        assert result["success"] is True
        assert result["count"] == 2
        assert v2.add.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self, v2):
        async def fake_add(content, metadata):
            if content == "bad":
                return {"success": False, "error": "bad content"}
            return {"success": True}

        v2.add = fake_add  # type: ignore[assignment]
        items = [("good", {}), ("bad", {})]
        result = await v2.add_batch(items)
        assert result["success"] is False
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_batch_exception(self, v2):
        async def fake_add(content, metadata):
            if content == "boom":
                raise ValueError("crash")
            return {"success": True}

        v2.add = fake_add  # type: ignore[assignment]
        items = [("good", {}), ("boom", {})]
        result = await v2.add_batch(items)
        assert result["success"] is False
        assert result["count"] == 1


# ─── search_batch / Cache ──────────────────────────────────────────


class TestSearchBatch:
    @pytest.mark.asyncio
    async def test_no_cache_hits_searches_all(self, v2):
        v2.search = AsyncMock(return_value=[{"text": "r1"}, {"text": "r2"}])  # type: ignore[assignment]
        results = await v2.search_batch(["q1", "q2"], top_k=3)
        assert len(results) == 2
        assert v2.search.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_hit_skips_search(self, v2):
        v2.search = AsyncMock(return_value=[{"text": "cached"}])  # type: ignore[assignment]
        # First call populates cache
        await v2.search_batch(["q1"], top_k=3)
        assert v2.search.call_count == 1

        # Second call should hit cache
        results = await v2.search_batch(["q1"], top_k=3)
        assert v2.search.call_count == 1  # not incremented
        assert results[0][0]["text"] == "cached"

    @pytest.mark.asyncio
    async def test_cache_returns_empty_list(self, v2):
        """Cached empty result is reused."""
        v2.search = AsyncMock(return_value=[])  # type: ignore[assignment]
        await v2.search_batch(["q1"])
        v2.search.reset_mock()
        results = await v2.search_batch(["q1"])
        assert results == [[]]
        v2.search.assert_not_called()


# ─── Cache internals ───────────────────────────────────────────────


class TestCacheInternals:
    def test_cache_key_format(self, v2):
        k1 = v2._make_cache_key("hello", 5, None)
        k2 = v2._make_cache_key("hello", 5, None)
        assert k1 == k2
        k3 = v2._make_cache_key("hello", 10, {"x": 1})
        assert k1 != k3

    @pytest.mark.asyncio
    async def test_cache_disabled(self, v2):
        v2._cache_enabled = False
        assert await v2._get_from_cache("any") is None

    @pytest.mark.asyncio
    async def test_put_and_get(self, v2):
        await v2._put_to_cache("k", ["result"])
        cached = await v2._get_from_cache("k")
        assert cached == ["result"]

    @pytest.mark.asyncio
    async def test_cache_ttl(self, v2):
        v2._cache_ttl = -1  # expired immediately
        await v2._put_to_cache("k", ["data"])
        cached = await v2._get_from_cache("k")
        assert cached is None  # expired

    @pytest.mark.asyncio
    async def test_lru_eviction(self, v2):
        v2._cache_max_size = 2
        await v2._put_to_cache("a", [1])
        await v2._put_to_cache("b", [2])
        await v2._put_to_cache("c", [3])
        assert await v2._get_from_cache("a") is None
        assert await v2._get_from_cache("b") == [2]

    @pytest.mark.asyncio
    async def test_clear_cache(self, v2):
        await v2._put_to_cache("k", ["v"])
        v2._cache_hits = 10
        v2._cache_misses = 5
        await v2.clear_cache()
        assert v2._query_cache == {}
        assert v2._cache_hits == 0
        assert v2._cache_misses == 0

    def test_cache_stats(self, v2):
        v2._cache_hits = 8
        v2._cache_misses = 2
        v2._query_cache["dummy"] = CacheEntry([], 0)
        stats = v2.get_cache_stats()
        assert stats["hits"] == 8
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 80.0
        assert stats["size"] == 1
        assert stats["max_size"] == 5


# ─── warmup ────────────────────────────────────────────────────────


class TestWarmup:
    @pytest.mark.asyncio
    async def test_warmup_calls_search_batch(self, v2):
        v2.search_batch = AsyncMock(return_value=[[], []])  # type: ignore[assignment]
        await v2.warmup(["q1", "q2"], top_k=3)
        v2.search_batch.assert_awaited_once_with(["q1", "q2"], 3)


# ─── get_stats ─────────────────────────────────────────────────────


class TestGetStats:
    @pytest.mark.asyncio
    async def test_get_stats_includes_cache(self, v2):
        v2.conversations.count.return_value = 2
        v2.knowledge.count.return_value = 3
        v2.preferences.count.return_value = 1
        stats = await v2.get_stats()
        assert stats["conversations"] == 2
        assert stats["cache"]["hits"] == 0
        assert stats["cache"]["hit_rate"] == 0.0


# ─── Decay — pure calculation ──────────────────────────────────────


class TestDecayMath:
    """Pure-function decay calculations (no mocks needed)."""

    def test_calculate_decay_now(self, v2):
        """Elapsed = 0 -> intensity = 1.0"""
        intensity = v2._calculate_decay(time.time(), repetition_interval=10)
        assert intensity == pytest.approx(1.0, abs=0.001)

    def test_calculate_decay_past(self, v2):
        """10 hours ago with interval=10 -> known value ~0.287."""
        past = time.time() - 10 * 3600
        intensity = v2._calculate_decay(past, repetition_interval=10)
        # decay_coef for 10h = 0.8, intensity = e^(-10 / (0.8 * 10)) = e^(-1.25)
        assert intensity == pytest.approx(0.287, abs=0.01)

    def test_calculate_decay_clamped(self, v2):
        """Intensity clamps at 1.0 for recent entries and does not overflow."""
        # A moderately future timestamp gives elapsed_hours slightly negative,
        # intensity stays near 1.0 without overflow
        future = time.time() + 3600  # 1 hour in the future
        intensity = v2._calculate_decay(future, repetition_interval=5)
        assert 0.0 <= intensity <= 1.0
        assert intensity == pytest.approx(1.0, abs=0.01)

    def test_calculate_decay_unknown_interval(self, v2):
        """Unknown repetition_interval uses default coef 0.5."""
        past = time.time() - 5 * 3600
        intensity = v2._calculate_decay(past, repetition_interval=999)
        # intensity = e^(-5 / (0.5 * 10)) = e^(-1)
        assert intensity == pytest.approx(0.368, abs=0.01)

    def test_get_intensity_level(self, v2):
        assert v2._get_intensity_level(0.9) == MemoryIntensity.ALIVE
        assert v2._get_intensity_level(0.6) == MemoryIntensity.NORMAL
        assert v2._get_intensity_level(0.3) == MemoryIntensity.FADING
        assert v2._get_intensity_level(0.1) == MemoryIntensity.FORGOTTEN


# ─── Decay — collection-level ──────────────────────────────────────


class TestDecayCollection:
    @pytest.mark.asyncio
    async def test_decay_collection_empty(self, v2):
        v2.conversations.get.return_value = {"ids": [], "metadatas": []}
        stats = await v2._decay_collection(v2.conversations, "conversations", 10)
        assert stats == {"checked": 0, "decayed": 0, "forgotten": 0}

    @pytest.mark.asyncio
    async def test_check_decay_all(self, v2):
        for coll in [v2.conversations, v2.knowledge, v2.preferences]:
            coll.get.return_value = {"ids": [], "metadatas": []}
        stats = await v2.check_decay("all")
        assert stats["checked"] == 0

    @pytest.mark.asyncio
    async def test_trigger_decay_check_session(self, v2):
        v2.conversations.get.return_value = {"ids": ["id1"], "metadatas": [{}]}
        stats = await v2.trigger_decay_check("session-1")
        assert stats["checked"] == 1

    @pytest.mark.asyncio
    async def test_trigger_decay_check_all(self, v2):
        for coll in [v2.conversations, v2.knowledge, v2.preferences]:
            coll.get.return_value = {"ids": [], "metadatas": []}
        stats = await v2.trigger_decay_check()
        assert stats["checked"] == 0


# ─── Memory intensity helpers ──────────────────────────────────────


class TestMemoryIntensity:
    @pytest.mark.asyncio
    async def test_update_memory_intensity(self, v2):
        v2.conversations.get.return_value = {
            "ids": ["doc1"],
            "metadatas": [{"intensity": 0.5}],
        }
        await v2._update_memory_intensity("doc1", "conversations", increment=0.3)
        v2.conversations.update.assert_called_once()
        _args, kwargs = v2.conversations.update.call_args
        assert kwargs["ids"] == ["doc1"]
        assert kwargs["metadatas"][0]["intensity"] == 0.8

    @pytest.mark.asyncio
    async def test_update_memory_intensity_capped(self, v2):
        v2.conversations.get.return_value = {
            "ids": ["doc1"],
            "metadatas": [{"intensity": 0.9}],
        }
        await v2._update_memory_intensity("doc1", "conversations", increment=0.3)
        _args, kwargs = v2.conversations.update.call_args
        assert kwargs["metadatas"][0]["intensity"] == 1.0

    def test_get_memory_intensity(self, v2):
        v2.conversations.get.return_value = {
            "ids": ["doc1"],
            "metadatas": [{"intensity": 0.9, "last_accessed": 1000}],
        }
        result = v2.get_memory_intensity("doc1", "conversations")
        assert result["intensity"] == 0.9
        assert result["level"] == MemoryIntensity.ALIVE

    def test_get_memory_intensity_missing(self, v2):
        v2.conversations.get.return_value = {"ids": [], "metadatas": []}
        result = v2.get_memory_intensity("nope", "conversations")
        assert result is None

    def test_get_memory_intensity_bad_collection(self, v2):
        result = v2.get_memory_intensity("x", "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_reinforce_memory(self, v2):
        v2.conversations.get.return_value = {
            "ids": ["doc1"],
            "metadatas": [{"intensity": 0.5, "repetition_count": 2}],
        }
        result = await v2.reinforce_memory("doc1", "conversations")
        assert result is True
        _args, kwargs = v2.conversations.update.call_args
        assert kwargs["metadatas"][0]["intensity"] == 0.7
        assert kwargs["metadatas"][0]["repetition_count"] == 3

    @pytest.mark.asyncio
    async def test_reinforce_memory_missing(self, v2):
        v2.conversations.get.return_value = {"ids": [], "metadatas": []}
        result = await v2.reinforce_memory("nope", "conversations")
        assert result is False

    def test_get_timestamp_float(self, v2):
        meta = {"last_accessed": 12345.0}
        ts = v2._get_timestamp(meta)
        assert ts == 12345.0

    def test_get_timestamp_iso_string(self, v2):
        meta = {"timestamp": "2025-01-01T12:00:00"}
        ts = v2._get_timestamp(meta)
        # fromisoformat parses without timezone as local time (UTC+8 here: 2025-01-01 04:00:00 UTC)
        assert ts == 1735704000.0

    def test_get_timestamp_fallback(self, v2):
        ts = v2._get_timestamp({})
        assert ts is not None  # returns time.time()
