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
    await vm.add("我叫张三", {"type": "preference", "key": "name"})
    results = await vm.search("用户叫什么名字？")

Author: Plector
Version: 1.0.0
Created: 2026-04-05
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

DB_PATH = "data/vector_memory"


class VectorMemory:
    """基于 ChromaDB 的向量记忆"""

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

    def _generate_id(self, text: str, prefix: str = "") -> str:
        """生成唯一 ID"""
        hash_val = hashlib.md5(text.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}_{hash_val}"

    async def add_conversation(
        self,
        text: str,
        session_id: str,
        role: str,
    ) -> str:
        """添加对话记忆"""
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

    async def add_knowledge(
        self,
        text: str,
        topic: str,
        source: str = "",
    ) -> str:
        """添加知识记忆"""
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

    async def add_preference(
        self,
        key: str,
        value: str,
    ) -> str:
        """添加用户偏好"""
        try:
            text = f"{key}: {value}"
            doc_id = f"pref_{key}"
            # 更新已有偏好
            try:
                self.preferences.delete(ids=[doc_id])
            except Exception:
                pass
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
        try:
            results = []

            collections = []
            if collection == "all":
                collections = [
                    ("conversations", self.conversations),
                    ("knowledge", self.knowledge),
                    ("preferences", self.preferences),
                ]
            elif collection == "conversations":
                collections = [("conversations", self.conversations)]
            elif collection == "knowledge":
                collections = [("knowledge", self.knowledge)]
            elif collection == "preferences":
                collections = [("preferences", self.preferences)]

            for name, coll in collections:
                try:
                    # 构建过滤条件
                    where = None
                    if name == "conversations" and session_id:
                        where = {"session_id": session_id}

                    result = coll.query(
                        query_texts=[query],
                        n_results=n_results,
                        where=where,
                    )

                    if result and result["documents"]:
                        for i, doc in enumerate(result["documents"][0]):
                            results.append(
                                {
                                    "text": doc,
                                    "metadata": result["metadatas"][0][i] if result["metadatas"] else {},
                                    "distance": result["distances"][0][i] if result["distances"] else 0,
                                    "collection": name,
                                }
                            )
                except Exception as e:
                    logger.warning(f"搜索 {name} 失败: {e}")

            # 按距离排序（距离越小越相关）
            results.sort(key=lambda x: x["distance"])
            return results[:n_results]

        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []

    async def get_stats(self) -> dict[str, int]:
        """获取记忆统计"""
        return {
            "conversations": self.conversations.count(),
            "knowledge": self.knowledge.count(),
            "preferences": self.preferences.count(),
        }

    async def delete_session(self, session_id: str):
        """删除指定会话的所有记忆"""
        try:
            result = self.conversations.get(where={"session_id": session_id})
            if result and result["ids"]:
                self.conversations.delete(ids=result["ids"])
        except Exception as e:
            logger.error(f"删除会话记忆失败: {e}")
