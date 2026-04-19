#!/usr/bin/env python3
"""
记忆管理技能 - 存储和查询对话历史、用户偏好、知识记忆

功能：
    1. 保存对话记录
    2. 获取对话历史
    3. 保存/获取用户偏好
    4. 保存/搜索知识记忆
    5. 8种关联记忆模式

Author: Plector
Version: 2.0.0
Created: 2026-04-05
Updated: 2026-04-19 (添加艾宾浩斯遗忘曲线和8种关联记忆模式)
"""

import asyncio
import logging
import re
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from core.event_bus_v2 import get_event_bus_v2 as get_event_bus
from core.vector_memory_v2 import VectorMemoryV2 as VectorMemory

logger = logging.getLogger(__name__)

DB_PATH = str(Path(__file__).parent.parent.parent / "data" / "plector.db")


class AssociativeMode(Enum):
    """8种关联记忆模式"""

    SEMANTIC_SIMILARITY = "semantic_similarity"  # 语义相似性 (P1)
    CONTEXT_TRIGGERS = "context_triggers"  # 上下文触发 (P2)
    RELATED_EXPANSION = "related_expansion"  # 相关扩展 (P2)
    TEMPORAL = "temporal"  # 时间维度 (P2)
    SPACED_REPETITION = "spaced_repetition"  # 间隔复习 (P2)
    EMOTIONAL_WEIGHT = "emotional_weight"  # 情感权重 (P3)
    IMPORTANCE_SCORE = "importance_score"  # 重要性评分 (P3)
    PATTERN_MATCH = "pattern_match"  # 模式匹配 (P3)


def get_connection():
    """获取数据库连接"""
    db = Path(DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db))


# 上下文触发关键词
CONTEXT_TRIGGER_KEYWORDS = {
    "代码": ["代码", "编程", "函数", "类", "实现", "bug", "debug"],
    "项目": ["项目", "开发", "需求", "功能", "模块", "重构"],
    "文档": ["文档", "说明", "注释", "readme", "规范"],
    "测试": ["测试", "单元测试", "用例", "回归", "验证"],
    "部署": ["部署", "上线", "发布", "服务器", "环境"],
    "问题": ["问题", "错误", "异常", "失败", "修复", "解决"],
    "学习": ["学习", "研究", "探索", "了解", "掌握"],
    "优化": ["优化", "性能", "改进", "提升", "重构"],
}


class SkillHandler:
    """记忆管理技能处理器"""

    def __init__(self):
        self.name = "memory"
        self.vector_memory = VectorMemory()

    # ========== 8种关联记忆模式 ==========

    async def associative_search(
        self, query: str, mode: str = "semantic_similarity", limit: int = 5, **kwargs
    ) -> dict[str, Any]:
        """
        关联记忆搜索 - 8种模式

        Args:
            query: 搜索查询
            mode: 关联模式 (semantic_similarity/context_triggers/related_expansion/
                        temporal/spaced_repetition/emotional_weight/
                        importance_score/pattern_match)
            limit: 返回结果数

        Returns:
            dict: {"success": bool, "data": {"results": list}, "error": str}
        """
        try:
            results = []

            if mode == "semantic_similarity":
                results = await self._semantic_similarity_search(query, limit)
            elif mode == "context_triggers":
                results = await self._context_triggers_search(query, limit)
            elif mode == "related_expansion":
                results = await self._related_expansion_search(query, limit)
            elif mode == "temporal":
                results = await self._temporal_search(query, limit, **kwargs)
            elif mode == "spaced_repetition":
                results = await self._spaced_repetition_search(query, limit)
            elif mode == "emotional_weight":
                results = await self._emotional_weight_search(query, limit)
            elif mode == "importance_score":
                results = await self._importance_score_search(query, limit)
            elif mode == "pattern_match":
                results = await self._pattern_match_search(query, limit, **kwargs)
            else:
                return {"success": False, "data": None, "error": f"Unknown mode: {mode}"}

            return {"success": True, "data": {"results": results, "mode": mode}, "error": None}
        except Exception as e:
            logger.error(f"关联搜索失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def _semantic_similarity_search(self, query: str, limit: int) -> list:
        """P1: 语义相似性搜索 - 向量余弦相似度"""
        results = await self.vector_memory.search(
            query=query,
            collection="all",
            n_results=limit,
        )
        return results

    async def _context_triggers_search(self, query: str, limit: int) -> list:
        """P2: 上下文触发搜索 - 关键词上下文触发"""
        matched_categories = []
        query_lower = query.lower()

        # 匹配上下文类别
        for category, keywords in CONTEXT_TRIGGER_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                matched_categories.append(category)

        # 如果没有匹配类别，返回语义搜索结果
        if not matched_categories:
            return await self._semantic_similarity_search(query, limit)

        # 从SQLite中搜索匹配类别的记忆
        conn = get_connection()
        cursor = conn.cursor()

        like_patterns = [f"%{cat}%" for cat in matched_categories]

        cursor.execute(
            f"SELECT topic, content, source, created_at FROM knowledge "
            f"WHERE {' OR '.join(['topic LIKE ?' for _ in like_patterns])} "
            f"ORDER BY created_at DESC LIMIT ?",
            [*like_patterns, limit],
        )
        rows = cursor.fetchall()
        conn.close()

        results = [
            {
                "topic": row[0],
                "content": row[1],
                "source": row[2],
                "created_at": row[3],
                "match_type": "context_trigger",
                "categories": matched_categories,
            }
            for row in rows
        ]
        return results

    async def _related_expansion_search(self, query: str, limit: int) -> list:
        """P2: 相关扩展搜索 - 关联知识扩展"""
        # 先做语义搜索
        semantic_results = await self._semantic_similarity_search(query, limit)

        # 获取已找到的主题
        topics = set()
        for r in semantic_results:
            if "metadata" in r:
                topic = r["metadata"].get("topic", "")
                if topic:
                    topics.add(topic)

        # 搜索相关主题的知识
        if topics:
            conn = get_connection()
            cursor = conn.cursor()

            topic_list = list(topics)
            placeholders = ",".join(["?" for _ in topic_list])

            cursor.execute(
                f"SELECT topic, content, source, created_at FROM knowledge "
                f"WHERE topic IN ({placeholders}) ORDER BY created_at DESC",
                topic_list,
            )
            rows = cursor.fetchall()
            conn.close()

            related = [
                {
                    "topic": row[0],
                    "content": row[1],
                    "source": row[2],
                    "created_at": row[3],
                    "match_type": "related_expansion",
                }
                for row in rows
            ]

            # 合并结果
            all_results = semantic_results + related
            return all_results[:limit]

        return semantic_results

    async def _temporal_search(self, query: str, limit: int, **kwargs) -> list:
        """P2: 时间维度搜索 - 时间相关性"""
        time_range = kwargs.get("time_range", "all")  # all/today/week/month

        now = datetime.now()
        if time_range == "today":
            start_date = now.replace(hour=0, minute=0, second=0)
        elif time_range == "week":
            start_date = now - timedelta(days=7)
        elif time_range == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = None

        # 先获取语义结果
        semantic_results = await self._semantic_similarity_search(query, limit)

        if start_date:
            # 过滤时间范围
            filtered = []
            for r in semantic_results:
                meta = r.get("metadata", {})
                timestamp_str = meta.get("timestamp", "")
                if timestamp_str:
                    try:
                        if isinstance(timestamp_str, str):
                            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        else:
                            timestamp = datetime.fromtimestamp(timestamp_str)

                        if timestamp >= start_date:
                            filtered.append({**r, "match_type": "temporal"})
                    except Exception:
                        filtered.append({**r, "match_type": "temporal"})
                else:
                    filtered.append({**r, "match_type": "temporal"})
            return filtered[:limit]

        return [{**r, "match_type": "temporal"} for r in semantic_results]

    async def _spaced_repetition_search(self, query: str, limit: int) -> list:
        """P2: 间隔复习搜索 - 基于艾宾浩斯遗忘曲线"""
        try:
            # 检查所有记忆的衰减状态
            decay_stats = await self.vector_memory.check_decay(collection="all", repetition_interval=10)

            # 获取需要复习的记忆（FADING或FORGOTTEN状态）
            conn = get_connection()
            cursor = conn.cursor()

            # 查找较久没有复习的知识
            cursor.execute(
                "SELECT topic, content, source, created_at FROM knowledge "
                "WHERE datetime(created_at) < datetime('now', '-1 day') "
                "ORDER BY created_at ASC LIMIT ?",
                [limit],
            )
            rows = cursor.fetchall()
            conn.close()

            results = [
                {
                    "topic": row[0],
                    "content": row[1],
                    "source": row[2],
                    "created_at": row[3],
                    "match_type": "spaced_repetition",
                    "decay_stats": decay_stats,
                }
                for row in rows
            ]
            return results
        except Exception as e:
            logger.warning(f"间隔复习搜索失败: {e}")
            return await self._semantic_similarity_search(query, limit)

    async def _emotional_weight_search(self, query: str, limit: int) -> list:
        """P3: 情感权重搜索 - 带有情感标记的记忆优先"""
        # 搜索包含情感标记的记忆
        emotional_keywords = ["重要", "紧急", "关键", "必须", "一定", "绝对", "特别"]

        conn = get_connection()
        cursor = conn.cursor()

        like_patterns = [f"%{kw}%" for kw in emotional_keywords]
        placeholders = " OR ".join(["content LIKE ?" for _ in like_patterns])

        cursor.execute(
            f"SELECT topic, content, source, created_at FROM knowledge "
            f"WHERE {placeholders} ORDER BY created_at DESC LIMIT ?",
            [*like_patterns, limit],
        )
        rows = cursor.fetchall()
        conn.close()

        if rows:
            return [
                {
                    "topic": row[0],
                    "content": row[1],
                    "source": row[2],
                    "created_at": row[3],
                    "match_type": "emotional_weight",
                }
                for row in rows
            ]

        # 如果没有情感标记结果，返回语义搜索
        return await self._semantic_similarity_search(query, limit)

    async def _importance_score_search(self, query: str, limit: int) -> list:
        """P3: 重要性评分搜索 - 根据重要性标记排序"""
        importance_markers = ["!important", "!critical", "!priority", "[重要]", "[关键]"]

        conn = get_connection()
        cursor = conn.cursor()

        all_results = []
        for marker in importance_markers:
            cursor.execute(
                "SELECT topic, content, source, created_at FROM knowledge "
                "WHERE content LIKE ? ORDER BY created_at DESC",
                [f"%{marker}%"],
            )
            rows = cursor.fetchall()
            for row in rows:
                all_results.append(
                    {
                        "topic": row[0],
                        "content": row[1],
                        "source": row[2],
                        "created_at": row[3],
                        "match_type": "importance_score",
                        "marker": marker,
                    }
                )

        conn.close()

        if all_results:
            return all_results[:limit]

        return await self._semantic_similarity_search(query, limit)

    async def _pattern_match_search(self, query: str, limit: int, **kwargs) -> list:
        """P3: 模式匹配搜索 - 正则表达式模式匹配"""
        pattern = kwargs.get("pattern", query)

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT topic, content, source, created_at FROM knowledge ORDER BY created_at DESC LIMIT 100",
        )
        rows = cursor.fetchall()
        conn.close()

        matched = []
        for row in rows:
            if regex.search(row[1]) or regex.search(row[0]):
                matched.append(
                    {
                        "topic": row[0],
                        "content": row[1],
                        "source": row[2],
                        "created_at": row[3],
                        "match_type": "pattern_match",
                        "pattern": pattern,
                    }
                )

        return matched[:limit]

    def _save_conversation_sync(self, session_id: str, role: str, content: str):
        """同步保存对话记录"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        conn.commit()
        conn.close()

    async def save_conversation(self, session_id: str, role: str, content: str) -> dict[str, Any]:
        """保存对话记录"""
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._save_conversation_sync, session_id, role, content)

            # 同时存入向量库
            await self.vector_memory.add_conversation(
                text=content,
                session_id=session_id,
                role=role,
            )

            bus = get_event_bus()
            await bus.publish(
                "memory.stored",
                {"type": "conversation", "session_id": session_id},
                source="memory",
            )

            return {"success": True, "data": {"saved": True}, "error": None}
        except Exception as e:
            logger.error(f"保存对话失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _get_conversation_history_sync(self, session_id: str, limit: int) -> list[dict]:
        """同步获取对话历史"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"role": row[0], "content": row[1], "timestamp": row[2]} for row in reversed(rows)]

    async def get_conversation_history(self, session_id: str, limit=None) -> dict[str, Any]:
        """获取指定会话的对话历史"""
        try:
            if limit is None:
                limit = 10

            loop = asyncio.get_running_loop()
            messages = await loop.run_in_executor(None, self._get_conversation_history_sync, session_id, limit)

            bus = get_event_bus()
            await bus.publish(
                "memory.retrieved",
                {"type": "conversation", "count": len(messages)},
                source="memory",
            )

            return {"success": True, "data": {"messages": messages}, "error": None}
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _save_preference_sync(self, key: str, value: str):
        """同步保存用户偏好"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value),
        )
        conn.commit()
        conn.close()

    async def save_preference(self, key: str, value: str) -> dict[str, Any]:
        """保存用户偏好"""
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._save_preference_sync, key, value)

            # 同时存入向量库
            await self.vector_memory.add_preference(key=key, value=value)

            return {"success": True, "data": {"saved": True}, "error": None}
        except Exception as e:
            logger.error(f"保存偏好失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _get_preference_sync(self, key: str) -> str | None:
        """同步获取用户偏好"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    async def get_preference(self, key: str) -> dict[str, Any]:
        """获取用户偏好"""
        try:
            loop = asyncio.get_running_loop()
            value = await loop.run_in_executor(None, self._get_preference_sync, key)

            return {
                "success": True,
                "data": {"key": key, "value": value},
                "error": None,
            }
        except Exception as e:
            logger.error(f"获取偏好失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _save_knowledge_sync(self, topic: str, content: str, source: str):
        """同步保存知识记忆"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO knowledge (topic, content, source) VALUES (?, ?, ?)",
            (topic, content, source),
        )
        conn.commit()
        conn.close()

    async def save_knowledge(self, topic: str, content: str, source: str) -> dict[str, Any]:
        """保存知识记忆"""
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._save_knowledge_sync, topic, content, source)

            # 同时存入向量库
            await self.vector_memory.add_knowledge(
                text=content,
                topic=topic,
                source=source,
            )

            return {"success": True, "data": {"saved": True}, "error": None}
        except Exception as e:
            logger.error(f"保存知识失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _search_knowledge_sync(self, keyword: str) -> list[dict]:
        """同步搜索知识记忆"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT topic, content, source, created_at FROM knowledge "
            "WHERE topic LIKE ? OR content LIKE ? "
            "ORDER BY created_at DESC LIMIT 10",
            (f"%{keyword}%", f"%{keyword}%"),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "topic": row[0],
                "content": row[1],
                "source": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]

    def _search_knowledge_fts_sync(self, keyword: str, limit: int = 10) -> list[dict]:
        """使用 FTS5 全文搜索知识记忆"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # 使用 FTS5 MATCH 进行全文搜索
            cursor.execute(
                """
                SELECT k.topic, k.content, k.source, k.created_at
                FROM knowledge_fts fts
                JOIN knowledge k ON k.id = fts.rowid
                WHERE knowledge_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (keyword, limit),
            )
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            # FTS5 表不存在时回退到 LIKE 搜索
            return self._search_knowledge_sync(keyword)
        finally:
            conn.close()

        return [
            {
                "topic": row[0],
                "content": row[1],
                "source": row[2],
                "created_at": row[3],
                "search_type": "fts5",
            }
            for row in rows
        ]

    async def search_knowledge(self, keyword: str, use_fts: bool = True) -> dict[str, Any]:
        """搜索知识记忆"""
        try:
            loop = asyncio.get_running_loop()
            if use_fts:
                results = await loop.run_in_executor(None, self._search_knowledge_fts_sync, keyword, 10)
            else:
                results = await loop.run_in_executor(None, self._search_knowledge_sync, keyword)

            return {"success": True, "data": {"results": results}, "error": None}
        except Exception as e:
            logger.error(f"搜索知识失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def semantic_search(self, query: str, collection=None, limit=None) -> dict[str, Any]:
        """语义搜索记忆"""
        try:
            if collection is None:
                collection = "all"
            if limit is None:
                limit = 5

            results = await self.vector_memory.search(
                query=query,
                collection=collection,
                n_results=limit,
            )

            return {
                "success": True,
                "data": {"results": results, "count": len(results)},
                "error": None,
            }
        except Exception as e:
            logger.error(f"语义搜索失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _search_conversations_fts_sync(self, query: str, session_id: str = None, limit: int = 10) -> list[dict]:
        """使用 FTS5 全文搜索对话历史"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if session_id:
                cursor.execute(
                    """
                    SELECT c.role, c.content, c.timestamp, c.session_id
                    FROM conversations_fts fts
                    JOIN conversations c ON c.id = fts.rowid
                    WHERE conversations_fts MATCH ? AND c.session_id = ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (query, session_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT c.role, c.content, c.timestamp, c.session_id
                    FROM conversations_fts fts
                    JOIN conversations c ON c.id = fts.rowid
                    WHERE conversations_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (query, limit),
                )
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            # FTS5 表不存在时回退
            conn.close()
            return []
        finally:
            conn.close()

        return [
            {
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "session_id": row[3],
                "search_type": "fts5",
            }
            for row in rows
        ]

    async def full_text_search(self, query: str, collection: str = "all", session_id: str = None, limit: int = 10) -> dict[str, Any]:
        """
        FTS5 全文搜索

        Args:
            query: 搜索查询
            collection: 搜索集合 (all/conversations/knowledge)
            session_id: 可选的会话 ID 过滤
            limit: 返回结果数

        Returns:
            dict: {"success": bool, "data": {"results": list, "by_collection": dict}, "error": str}
        """
        try:
            loop = asyncio.get_running_loop()
            results = {"conversations": [], "knowledge": []}

            if collection in ("all", "conversations"):
                conv_results = await loop.run_in_executor(
                    None, self._search_conversations_fts_sync, query, session_id, limit
                )
                results["conversations"] = conv_results

            if collection in ("all", "knowledge"):
                know_results = await loop.run_in_executor(
                    None, self._search_knowledge_fts_sync, query, limit
                )
                results["knowledge"] = know_results

            return {
                "success": True,
                "data": {
                    "results": results["conversations"] + results["knowledge"],
                    "by_collection": results,
                    "query": query,
                },
                "error": None,
            }
        except Exception as e:
            logger.error(f"FTS5 搜索失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def memory_stats(self) -> dict[str, Any]:
        """获取记忆统计"""
        try:
            stats = await self.vector_memory.get_stats()
            return {
                "success": True,
                "data": stats,
                "error": None,
            }
        except Exception as e:
            logger.error(f"获取统计失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    # ========== 艾宾浩斯遗忘曲线支持 ==========

    async def check_memory_decay(self, collection: str = "all", repetition_interval: int = 10) -> dict[str, Any]:
        """
        检查记忆衰减状态

        Args:
            collection: 检查的集合（all / conversations / knowledge / preferences）
            repetition_interval: 复习间隔（小时）

        Returns:
            dict: {"success": bool, "data": {"checked": int, "decayed": int, "forgotten": int}, "error": str}
        """
        try:
            # 检查衰减
            decay_stats = await self.vector_memory.check_decay(
                collection=collection, repetition_interval=repetition_interval
            )

            # 发布事件
            bus = get_event_bus()
            await bus.publish(
                "memory.decay_checked",
                {"collection": collection, "stats": decay_stats},
                source="memory",
            )

            return {
                "success": True,
                "data": decay_stats,
                "error": None,
            }
        except Exception as e:
            logger.error(f"检查记忆衰减失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def reinforce_memory(self, doc_id: str, collection: str = "conversations") -> dict[str, Any]:
        """
        强化指定记忆

        Args:
            doc_id: 文档ID
            collection: 集合名称

        Returns:
            dict: {"success": bool, "data": {"reinforced": bool}, "error": str}
        """
        try:
            reinforced = await self.vector_memory.reinforce_memory(doc_id=doc_id, collection=collection)

            return {
                "success": True,
                "data": {"reinforced": reinforced},
                "error": None,
            }
        except Exception as e:
            logger.error(f"强化记忆失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}
