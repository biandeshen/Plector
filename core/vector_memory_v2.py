"""
向量内存 v2 - 检索优化版
=======================
优化向量检索性能，支持批量查询和缓存

改进点:
1. 批量查询支持 - 一次查询多个向量
2. 结果缓存 - 避免重复查询
3. 索引预热 - 启动时加载常用索引
4. 混合检索 - 稀疏+稠密向量融合
5. 艾宾浩斯遗忘曲线 - 记忆强度衰减管理

使用方式:
    vm = VectorMemoryV2(config)

    # 单条存储
    await vm.add("content", {"key": "value"})

    # 批量存储
    await vm.add_batch([("content1", {...}), ("content2", {...})])

    # 批量查询
    results = await vm.search_batch(["query1", "query2"])

    # 检查记忆衰减
    await vm.check_decay()
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum

from .vector_memory import VectorMemory

logger = logging.getLogger(__name__)


class MemoryIntensity(Enum):
    """记忆强度等级"""

    ALIVE = "alive"  # 活跃记忆 - 最近访问
    NORMAL = "normal"  # 正常记忆 - 定期复习
    FADING = "fading"  # 衰退记忆 - 需要复习
    FORGOTTEN = "forgotten"  # 遗忘记忆 - 可被清除


# 艾宾浩斯遗忘曲线配置
# 衰减系数对应不同复习间隔（单位：小时）
DECAY_COEFFICIENTS = {
    5: 0.9,  # 5小时间隔 - 高衰减率
    10: 0.8,  # 10小时间隔
    30: 0.5,  # 30小时间隔
    50: 0.3,  # 50小时间隔 - 低衰减率
}

# 记忆强度阈值
INTENSITY_THRESHOLDS = {
    MemoryIntensity.ALIVE: 0.8,
    MemoryIntensity.NORMAL: 0.5,
    MemoryIntensity.FADING: 0.2,
    MemoryIntensity.FORGOTTEN: 0.0,
}


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

        tasks = [self.add(content, metadata) for content, metadata in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(str(result))
            elif result.get("success"):
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

    # ========== 艾宾浩斯遗忘曲线 ==========

    def _calculate_decay(self, last_accessed: float, repetition_interval: int) -> float:
        """
        计算记忆衰减系数

        Args:
            last_accessed: 上次访问时间戳
            repetition_interval: 复习间隔（小时）

        Returns:
            float: 衰减后的记忆强度 (0.0 - 1.0)
        """
        elapsed_hours = (time.time() - last_accessed) / 3600
        decay_coef = DECAY_COEFFICIENTS.get(repetition_interval, 0.5)

        # 指数衰减模型: intensity = e^(-elapsed_hours / decay_coef * 10)
        intensity = pow(2.71828, -elapsed_hours / (decay_coef * 10))
        return max(0.0, min(1.0, intensity))

    def _get_intensity_level(self, intensity: float) -> MemoryIntensity:
        """根据强度值获取记忆等级"""
        if intensity >= INTENSITY_THRESHOLDS[MemoryIntensity.ALIVE]:
            return MemoryIntensity.ALIVE
        elif intensity >= INTENSITY_THRESHOLDS[MemoryIntensity.NORMAL]:
            return MemoryIntensity.NORMAL
        elif intensity >= INTENSITY_THRESHOLDS[MemoryIntensity.FADING]:
            return MemoryIntensity.FADING
        return MemoryIntensity.FORGOTTEN

    async def _update_memory_intensity(self, doc_id: str, collection_name: str, increment: float = 0.1):
        """
        更新记忆强度（通过更新元数据）

        Args:
            doc_id: 文档ID
            collection_name: 集合名称
            increment: 增量值
        """
        try:
            coll = getattr(self, collection_name, None)
            if not coll:
                return

            result = coll.get(ids=[doc_id])
            if result and result["metadatas"]:
                meta = result["metadatas"][0]
                current_intensity = meta.get("intensity", 1.0)
                new_intensity = min(1.0, current_intensity + increment)

                coll.update(
                    ids=[doc_id], metadatas=[{**meta, "intensity": new_intensity, "last_accessed": time.time()}]
                )
        except Exception as e:
            logger.warning(f"更新记忆强度失败: {e}")

    def _get_timestamp(self, meta: dict) -> float:
        """解析时间戳"""
        last_accessed = meta.get("last_accessed", meta.get("timestamp", 0))
        if isinstance(last_accessed, str):
            try:
                from datetime import datetime

                return datetime.fromisoformat(last_accessed).timestamp()
            except Exception:
                return time.time()
        return last_accessed

    async def _decay_collection(self, coll, name: str, repetition_interval: int) -> dict:
        """衰减单个集合的记忆"""
        stats = {"checked": 0, "decayed": 0, "forgotten": 0}
        try:
            # 使用 run_in_executor 避免阻塞事件循环
            loop = asyncio.get_running_loop()
            all_data = await loop.run_in_executor(None, lambda: coll.get())
            if not all_data or not all_data["ids"]:
                return stats

            for i, doc_id in enumerate(all_data["ids"]):
                meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
                last_accessed = self._get_timestamp(meta)
                current_intensity = meta.get("intensity", 1.0)
                new_intensity = self._calculate_decay(last_accessed, repetition_interval)

                stats["checked"] += 1

                if new_intensity < current_intensity:
                    stats["decayed"] += 1
                    updated_meta = {**meta, "intensity": new_intensity}
                    # 使用默认参数捕获变量值
                    await loop.run_in_executor(
                        None, lambda did=doc_id, umeta=updated_meta: coll.update(ids=[did], metadatas=[umeta])
                    )

                if new_intensity < INTENSITY_THRESHOLDS[MemoryIntensity.FADING]:
                    stats["forgotten"] += 1

        except Exception as e:
            logger.warning(f"检查 {name} 衰减失败: {e}")
        return stats

    async def check_decay(self, collection: str = "all", repetition_interval: int = 10) -> dict:
        """检查并应用记忆衰减"""
        stats = {"checked": 0, "decayed": 0, "forgotten": 0}

        collections_map = {
            "all": [
                ("conversations", self.conversations),
                ("knowledge", self.knowledge),
                ("preferences", self.preferences),
            ],
            "conversations": [("conversations", self.conversations)],
            "knowledge": [("knowledge", self.knowledge)],
            "preferences": [("preferences", self.preferences)],
        }
        collections_to_check = collections_map.get(collection, collections_map["all"])

        for name, coll in collections_to_check:
            coll_stats = await self._decay_collection(coll, name, repetition_interval)
            stats["checked"] += coll_stats["checked"]
            stats["decayed"] += coll_stats["decayed"]
            stats["forgotten"] += coll_stats["forgotten"]

        return stats

    async def trigger_decay_check(self, session_id: str | None = None) -> dict:
        """
        对话触发衰减检查 - 当用户发起对话时调用

        Args:
            session_id: 会话ID，如果提供则只检查该会话的记忆

        Returns:
            dict: 衰减检查结果
        """
        if session_id:
            # 只检查指定会话的记忆
            try:
                result = self.conversations.get(where={"session_id": session_id})
                if result and result["ids"]:
                    doc_ids = result["ids"]
                    return await self._decay_session_memories(doc_ids)
            except Exception as e:
                logger.warning(f"会话 {session_id} 衰减检查失败: {e}")
                return {"checked": 0, "decayed": 0, "forgotten": 0}
        else:
            # 检查所有对话记忆
            return await self.check_decay("conversations")

    async def _decay_session_memories(self, doc_ids: list[str]) -> dict:
        """衰减会话记忆"""
        stats = {"checked": 0, "decayed": 0, "forgotten": 0}

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: self.conversations.get(ids=doc_ids))
            if not result or not result["ids"]:
                return stats

            for i, doc_id in enumerate(result["ids"]):
                meta = result["metadatas"][i] if result["metadatas"] else {}
                last_accessed = meta.get("last_accessed", meta.get("timestamp", 0))

                if isinstance(last_accessed, str):
                    try:
                        from datetime import datetime

                        last_accessed = datetime.fromisoformat(last_accessed).timestamp()
                    except Exception:
                        last_accessed = time.time()

                current_intensity = meta.get("intensity", 1.0)
                new_intensity = self._calculate_decay(last_accessed, repetition_interval=10)

                stats["checked"] += 1

                if new_intensity < current_intensity:
                    stats["decayed"] += 1
                    updated_meta = {**meta, "intensity": new_intensity}
                    # 使用默认参数捕获变量值
                    await loop.run_in_executor(
                        None,
                        lambda did=doc_id, umeta=updated_meta: self.conversations.update(ids=[did], metadatas=[umeta]),
                    )

                if new_intensity < INTENSITY_THRESHOLDS[MemoryIntensity.FADING]:
                    stats["forgotten"] += 1

        except Exception as e:
            logger.warning(f"会话记忆衰减失败: {e}")

        return stats

    def get_memory_intensity(self, doc_id: str, collection: str = "conversations") -> dict | None:
        """
        获取指定记忆的强度信息

        Args:
            doc_id: 文档ID
            collection: 集合名称

        Returns:
            dict: {"intensity": float, "level": MemoryIntensity, "last_accessed": float}
        """
        try:
            coll = getattr(self, collection, None)
            if not coll:
                return None

            result = coll.get(ids=[doc_id])
            if result and result["metadatas"]:
                meta = result["metadatas"][0]
                intensity = meta.get("intensity", 1.0)
                return {
                    "intensity": intensity,
                    "level": self._get_intensity_level(intensity),
                    "last_accessed": meta.get("last_accessed", meta.get("timestamp", 0)),
                }
        except Exception as e:
            logger.warning(f"获取记忆强度失败: {e}")
        return None

    async def reinforce_memory(self, doc_id: str, collection: str = "conversations") -> bool:
        """
        强化记忆 - 调用时增加记忆强度

        Args:
            doc_id: 文档ID
            collection: 集合名称

        Returns:
            bool: 是否成功
        """
        try:
            coll = getattr(self, collection, None)
            if not coll:
                return False

            result = coll.get(ids=[doc_id])
            if result and result["metadatas"]:
                meta = result["metadatas"][0]
                current_intensity = meta.get("intensity", 0.5)
                # 强化增幅
                new_intensity = min(1.0, current_intensity + 0.2)

                updated_meta = {
                    **meta,
                    "intensity": new_intensity,
                    "last_accessed": time.time(),
                    "repetition_count": meta.get("repetition_count", 0) + 1,
                }
                coll.update(ids=[doc_id], metadatas=[updated_meta])
                return True
        except Exception as e:
            logger.warning(f"强化记忆失败: {e}")
        return False
