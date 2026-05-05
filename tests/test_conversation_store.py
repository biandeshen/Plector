import contextlib
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.conversation_store import ConversationStore


@pytest.fixture
def store():
    """创建使用临时数据库的 ConversationStore"""
    tmp = tempfile.mktemp(suffix=".db")
    s = ConversationStore(db_path=tmp)
    yield s
    s.close()
    with contextlib.suppress(PermissionError):
        Path(tmp).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_save_persists_to_db(store):
    """save() 应写入 SQLite 数据库"""
    await store.save("test_session", "user", "你好")
    await store.save("test_session", "assistant", "你好，有什么可以帮助你的？")

    conn = sqlite3.connect(store.db_path)
    rows = conn.execute("SELECT session_id, role, content FROM conversations ORDER BY id").fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0] == ("test_session", "user", "你好")
    assert rows[1] == ("test_session", "assistant", "你好，有什么可以帮助你的？")


@pytest.mark.asyncio
async def test_save_failure_does_not_raise(store):
    """save() 在数据库异常时应静默降级，不抛异常"""
    with patch.object(store, "_get_conn", side_effect=sqlite3.OperationalError("模拟数据库错误")):
        await store.save("test_session", "user", "test")


def test_close_cleans_up(store):
    """close() 后再次 _get_conn 应创建新连接"""
    old_conn = store._get_conn()
    store.close()
    new_conn = store._get_conn()
    assert old_conn is not new_conn


def test_thread_local_isolation():
    """不同线程的 _get_conn 应返回不同连接"""
    import threading

    store = ConversationStore(db_path=tempfile.mktemp(suffix=".db"))
    results = {}

    def get_conn_in_thread(name):
        results[name] = store._get_conn()

    t = threading.Thread(target=get_conn_in_thread, args=("thread",))
    t.start()
    t.join()

    main_conn = store._get_conn()
    assert main_conn is not results["thread"]

    store.close()
    results["thread"].close()
    Path(store.db_path).unlink(missing_ok=True)
