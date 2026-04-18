#!/usr/bin/env python3
"""
记忆管理技能 - 存储和查询对话历史、用户偏好、知识记忆

功能：
    1. 保存对话记录
    2. 获取对话历史
    3. 保存/获取用户偏好
    4. 保存/搜索知识记忆

Author: Plector
Version: 1.0.0
Created: 2026-04-05
"""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Any

from core.event_bus import get_event_bus
from core.vector_memory import VectorMemory

logger = logging.getLogger(__name__)

DB_PATH = "data/plector.db"


def get_connection():
    """获取数据库连接"""
    db = Path(DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db))


class SkillHandler:
    """记忆管理技能处理器"""

    def __init__(self):
        self.name = "memory"
        self.vector_memory = VectorMemory()

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
            "SELECT role, content, timestamp FROM conversations "
            "WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
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
            "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) " "VALUES (?, ?, CURRENT_TIMESTAMP)",
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

    async def search_knowledge(self, keyword: str) -> dict[str, Any]:
        """搜索知识记忆"""
        try:
            loop = asyncio.get_running_loop()
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
