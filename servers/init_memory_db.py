#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化记忆数据库

创建记忆相关的表结构
"""

import sqlite3
from pathlib import Path


def init_memory_db(db_path="data/plector.db"):
    """初始化记忆数据库"""
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    # 对话历史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 用户偏好表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 知识记忆表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建 FTS5 虚拟表用于全文搜索
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
            content,
            session_id,
            role,
            content='conversations',
            content_rowid='id'
        )
    """)

    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
            topic,
            content,
            source,
            content='knowledge',
            content_rowid='id'
        )
    """)

    # 创建触发器保持 FTS 表同步
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS conversations_ai AFTER INSERT ON conversations BEGIN
            INSERT INTO conversations_fts(rowid, content, session_id, role)
            VALUES (new.id, new.content, new.session_id, new.role);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS conversations_ad AFTER DELETE ON conversations BEGIN
            INSERT INTO conversations_fts(conversations_fts, rowid, content, session_id, role)
            VALUES ('delete', old.id, old.content, old.session_id, old.role);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS conversations_au AFTER UPDATE ON conversations BEGIN
            INSERT INTO conversations_fts(conversations_fts, rowid, content, session_id, role)
            VALUES ('delete', old.id, old.content, old.session_id, old.role);
            INSERT INTO conversations_fts(rowid, content, session_id, role)
            VALUES (new.id, new.content, new.session_id, new.role);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
            INSERT INTO knowledge_fts(rowid, topic, content, source)
            VALUES (new.id, new.topic, new.content, new.source);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, content, source)
            VALUES ('delete', old.id, old.topic, old.content, old.source);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, topic, content, source)
            VALUES ('delete', old.id, old.topic, old.content, old.source);
            INSERT INTO knowledge_fts(rowid, topic, content, source)
            VALUES (new.id, new.topic, new.content, new.source);
        END
    """)

    conn.commit()
    conn.close()
    print(f"记忆数据库初始化完成: {db_path}")


if __name__ == "__main__":
    init_memory_db()
