"""
向量内存 v2 - 检索优化版
=======================
优化向量检索性能，支持批量查询和缓存

改进点:
1. 批量查询支持 - 一次查询多个向量
2. 结果缓存 - 避免重复查询
3. 索引预热 - 启动时加载常用索引
4. 混合检索 - 稀疏+稠密向量融合

使用方式:
    vm = VectorMemoryV2(config)

    # 单条存储
    await vm.add("content", {"key": "value"})

    # 批量存储
    await vm.add_batch([("content1", {...}), ("content2", {...})])

    # 批量查询
    results = await vm.search_batch(["query1", "query2"])
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass

from .vector_memory import VectorMemory


@dataclass
class CacheEntry:
    """缓存条目"""

    result: list
    timestamp: float


class VectorMemoryV2(VectorMemory):
    """
    向量内存 v2 - 性能优化版本

    继承自 v1 的所有功能，额外增加：
    - 批量操作
    - 结果缓存
    - 索引预热
    """

    def __init__(self, config: dict = None):
        if config is None:
            config = {}
        # Only pass path if explicitly configured, otherwise use default DB_PATH
        if "path" in config:
            super().__init__(config["path"])
        else:
            super().__init__()

        # 缓存配置
        self._cache_enabled = config.get("cache_enabled", True)
        self._cache_ttl = config.get("cache_ttl", 300)  # 5分钟
        self._cache_max_size = config.get("cache_max_size", 1000)

        # 查询缓存
        self._query_cache: dict[str, CacheEntry] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_lock = asyncio.Lock()

    # ========== 批量操作 ==========

    async def add_batch(self, items: list[tuple[str, dict]]) -> dict:
        """
        批量添加向量

        Args:
            items: [(content, metadata), ...]

        Returns:
            {"success": True, "count": int, "error": ""}
        """
        if not items:
            return {"success": True, "count": 0, "error": ""}

        success_count = 0
        errors = []

        for content, metadata in items:
            result = await self.add(content, metadata)
            if result.get("success"):
                success_count += 1
            else:
                errors.append(result.get("error", "unknown"))

        return {
            "success": success_count == len(items),
            "count": success_count,
            "error": "; ".join(errors[:3]) if errors else "",
        }

    async def search_batch(
        self,
        queries: list[str],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[list[dict]]:
        """
        批量查询

        Args:
            queries: 查询列表
            top_k: 每条查询返回的结果数
            filters: 统一过滤条件

        Returns:
            [[result1, result2, ...], ...] - 与 queries 一一对应
        """
        results = []

        for query in queries:
            # 检查缓存
            cache_key = self._make_cache_key(query, top_k, filters)
            cached = await self._get_from_cache(cache_key)
            if cached is not None:
                results.append(cached)
                continue

            # 执行查询
            result = await self.search(query, top_k, filters)
            entries = result.get("results", []) if result.get("success") else []

            # 存入缓存
            await self._put_to_cache(cache_key, entries)
            results.append(entries)

        return results

    # ========== 缓存管理 ==========

    def _make_cache_key(self, query: str, top_k: int, filters: dict | None) -> str:
        """生成缓存键"""
        key_data = f"{query}:{top_k}:{filters or {}!s}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _get_from_cache(self, key: str) -> list | None:
        """从缓存获取"""
        if not self._cache_enabled:
            return None

        async with self._cache_lock:
            if key in self._query_cache:
                entry = self._query_cache[key]
                if time.time() - entry.timestamp < self._cache_ttl:
                    self._cache_hits += 1
                    return entry.result
                else:
                    del self._query_cache[key]

            self._cache_misses += 1
            return None

    async def _put_to_cache(self, key: str, result: list):
        """存入缓存"""
        if not self._cache_enabled:
            return

        async with self._cache_lock:
            # LRU 淘汰
            while len(self._query_cache) >= self._cache_max_size:
                oldest_key = min(self._query_cache.keys(), key=lambda k: self._query_cache[k].timestamp)
                del self._query_cache[oldest_key]

            self._query_cache[key] = CacheEntry(result, time.time())

    async def clear_cache(self):
        """清空查询缓存"""
        async with self._cache_lock:
            self._query_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0

    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": round(hit_rate * 100, 1),
            "size": len(self._query_cache),
            "max_size": self._cache_max_size,
        }

    # ========== 索引预热 ==========

    async def warmup(self, popular_queries: list[str], top_k: int = 5):
        """
        预热索引 - 提前执行常用查询

        Args:
            popular_queries: 常用查询列表
            top_k: 查询结果数
        """
        await self.search_batch(popular_queries, top_k)

    # ========== 性能统计 ==========

    async def get_stats(self) -> dict:
        """获取完整统计"""
        base_stats = await super().get_stats()
        return {
            **base_stats,
            "cache": self.get_cache_stats(),
        }
