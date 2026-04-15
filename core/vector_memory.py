#!/usr/bin/env python3
"""
向量记忆模块 - 基于 ChromaDB 的语义记忆

功能：
    1. 将对话、偏好、知识存入向量数据库
    2. 语义搜索相关记忆
    3. 自动管理记忆生命周期

使用方式：
    from core.vector_memory import VectorMemory
    vm = VectorMemory()
    await vm.add("我姓张三", {"type": "preference", "key": "name"})
    results = await vm.search("用户叫什么名字？")

Author: Plector
Version: 1.0.0
Created: 2026-04-05
Updated: 2026-04-15 (添加 context_saver collection)
"""

import asyncio
import hashlib
import logging
from contextlib import suppress
from datetime import datetime
from typing import Any

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

DB_PATH = "data/vector_memory"


class VectorMemory:
    """
    基于 ChromaDB 的向量记忆
    """

    def __init__(self, path: str = DB_PATH):
        self.client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )

        # 对话记忆集合
        self.conversations = self.client.get_or_create_collection(
            name="conversations",
            metadata={"description": "对话历史的向量索引"},
        )

        # 知识记忆集合
        self.knowledge = self.client.get_or_create_collection(
            name="knowledge",
            metadata={"description": "知识记忆的向量索引"},
        )

        # 用户偏好集合
        self.preferences = self.client.get_or_create_collection(
            name="preferences",
            metadata={"description": "用户偏好的向量索引"},
        )

        # GSD 上下文保鲜集合 (P1-N)
        self.context_saver = self.client.get_or_create_collection(
            name="context_saver",
            metadata={"description": "GSD 上下文保鲜：goal/constraints/completed/in_progress"},
        )

    def _generate_id(self, text: str, prefix: str = "") -> str:
        """生成唯一 ID"""
        hash_val = hashlib.md5(text.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}_{hash_val}"

    def _add_conversation_sync(self, text: str, session_id: str, role: str) -> str:
        """同步添加对话记忆"""
        try:
            doc_id = self._generate_id(text, "conv")
            self.conversations.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[
                    {
                        "session_id": session_id,
                        "role": role,
                        "timestamp": datetime.now().isoformat(),
                    }
                ],
            )
            return doc_id
        except Exception as e:
            logger.error(f"添加对话向量失败: {e}")
            return ""

    async def add_conversation(
        self,
        text: str,
        session_id: str,
        role: str,
    ) -> str:
        """添加对话记忆"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._add_conversation_sync, text, session_id, role)

    def _add_knowledge_sync(self, text: str, topic: str, source: str) -> str:
        """同步添加知识记忆"""
        try:
            doc_id = self._generate_id(text, "know")
            self.knowledge.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[
                    {
                        "topic": topic,
                        "source": source,
                        "timestamp": datetime.now().isoformat(),
                    }
                ],
            )
            return doc_id
        except Exception as e:
            logger.error(f"添加知识向量失败: {e}")
            return ""

    async def add_knowledge(
        self,
        text: str,
        topic: str,
        source: str = "",
    ) -> str:
        """添加知识记忆"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._add_knowledge_sync, text, topic, source)

    def _add_preference_sync(self, key: str, value: str) -> str:
        """同步添加用户偏好"""
        try:
            text = f"{key}: {value}"
            doc_id = f"pref_{key}"
            # 更新已有偏好
            with suppress(Exception):
                self.preferences.delete(ids=[doc_id])
            self.preferences.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[
                    {
                        "key": key,
                        "value": value,
                        "timestamp": datetime.now().isoformat(),
                    }
                ],
            )
            return doc_id
        except Exception as e:
            logger.error(f"添加偏好向量失败: {e}")
            return ""

    async def add_preference(
        self,
        key: str,
        value: str,
    ) -> str:
        """添加用户偏好"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._add_preference_sync, key, value)

    # ========== GSD 上下文保鲜方法 (P1-N) ==========

    def _add_context_sync(
        self,
        goal: str,
        constraints: list,
        completed: list,
        in_progress: list,
        turns: int,
        session_id: str = "default",
    ) -> str:
        """
        同步添加 GSD 上下文保鲜数据

        参数:
            goal: 初始目标
            constraints: 约束条件列表
            completed: 已完成任务列表
            in_progress: 进行中任务列表
            turns: 对话轮次
            session_id: 会话 ID
        """
        try:
            doc_id = self._generate_id(goal, "ctx")
            document = f"Goal: {goal}\nConstraints: {', '.join(constraints)}\nCompleted: {', '.join(completed)}\nInProgress: {', '.join(in_progress)}"

            self.context_saver.add(
                ids=[doc_id],
                documents=[document],
                metadatas=[
                    {
                        "session_id": session_id,
                        "goal": goal,
                        "constraints": ",".join(constraints) if constraints else "",
                        "completed": ",".join(completed) if completed else "",
                        "in_progress": ",".join(in_progress) if in_progress else "",
                        "turns": turns,
                        "timestamp": datetime.now().isoformat(),
                    }
                ],
            )
            return doc_id
        except Exception as e:
            logger.error(f"添加上下文保鲜失败: {e}")
            return ""

    async def add_context(
        self,
        goal: str,
        constraints: list,
        completed: list,
        in_progress: list,
        turns: int,
        session_id: str = "default",
    ) -> str:
        """添加 GSD 上下文保鲜数据"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._add_context_sync,
            goal,
            constraints,
            completed,
            in_progress,
            turns,
            session_id,
        )

    def _get_latest_context_sync(self, session_id: str = "default") -> dict | None:
        """同步获取最新上下文"""
        try:
            result = self.context_saver.get(
                where={"session_id": session_id},
                limit=1,
            )
            if result and result["documents"]:
                meta = result["metadatas"][0]
                return {
                    "goal": meta.get("goal", ""),
                    "constraints": meta.get("constraints", "").split(",") if meta.get("constraints") else [],
                    "completed": meta.get("completed", "").split(",") if meta.get("completed") else [],
                    "in_progress": meta.get("in_progress", "").split(",") if meta.get("in_progress") else [],
                    "turns": meta.get("turns", 0),
                    "timestamp": meta.get("timestamp", ""),
                }
            return None
        except Exception as e:
            logger.error(f"获取上下文失败: {e}")
            return None

    async def get_latest_context(self, session_id: str = "default") -> dict | None:
        """获取最新上下文"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_latest_context_sync, session_id)

    # ================================================

    def _query_collection(self, coll, name: str, query: str, n_results: int, where: dict | None) -> list:
        """查询单个 collection"""
        result = coll.query(query_texts=[query], n_results=n_results, where=where)
        if result and result["documents"]:
            return [
                {
                    "text": doc,
                    "metadata": result["metadatas"][0][i] if result["metadatas"] else {},
                    "distance": result["distances"][0][i] if result["distances"] else 0,
                    "collection": name,
                }
                for i, doc in enumerate(result["documents"][0])
            ]
        return []

    def _search_sync(
        self,
        query: str,
        collection: str,
        n_results: int,
        session_id: str | None,
    ) -> list[dict[str, Any]]:
        """同步语义搜索"""
        try:
            results = []
            collection_map = {
                "all": [
                    ("conversations", self.conversations),
                    ("knowledge", self.knowledge),
                    ("preferences", self.preferences),
                ],
                "conversations": [("conversations", self.conversations)],
                "knowledge": [("knowledge", self.knowledge)],
                "preferences": [("preferences", self.preferences)],
            }
            colls = collection_map.get(collection, [])

            for name, coll in colls:
                try:
                    where = {"session_id": session_id} if name == "conversations" and session_id else None
                    results.extend(self._query_collection(coll, name, query, n_results, where))
                except Exception as e:
                    logger.warning(f"搜索 {name} 失败: {e}")

            results.sort(key=lambda x: x["distance"])
            return results[:n_results]

        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []

    async def search(
        self,
        query: str,
        collection: str = "all",
        n_results: int = 5,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        语义搜索记忆

        参数:
            query: 搜索查询
            collection: 搜索范围（all / conversations / knowledge / preferences）
            n_results: 返回结果数
            session_id: 限制会话范围（仅 conversations）

        返回:
            [{"text": str, "metadata": dict, "distance": float}, ...]
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, collection, n_results, session_id)

    def _get_stats_sync(self) -> dict[str, int]:
        """同步获取记忆统计"""
        return {
            "conversations": self.conversations.count(),
            "knowledge": self.knowledge.count(),
            "preferences": self.preferences.count(),
            "context_saver": self.context_saver.count(),
        }

    async def get_stats(self) -> dict[str, int]:
        """获取记忆统计"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_stats_sync)

    def _delete_session_sync(self, session_id: str):
        """同步删除会话记忆"""
        try:
            result = self.conversations.get(where={"session_id": session_id})
            if result and result["ids"]:
                self.conversations.delete(ids=result["ids"])
        except Exception as e:
            logger.error(f"删除会话记忆失败: {e}")

    async def delete_session(self, session_id: str):
        """删除指定会话的所有记忆"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._delete_session_sync, session_id)
