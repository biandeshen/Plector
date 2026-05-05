import asyncio
import logging
import sqlite3
import threading

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS conversations ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  session_id TEXT NOT NULL,"
    "  role TEXT NOT NULL,"
    "  content TEXT NOT NULL,"
    "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    ")"
)


class ConversationStore:
    """对话持久化存储，使用线程本地连接池避免每次新建连接"""

    def __init__(self, db_path: str = "data/plector.db"):
        self.db_path = db_path
        self._local = threading.local()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()
            self._local.conn = conn
        return self._local.conn

    def _save_sync(self, session_id: str, role: str, content: str):
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"保存对话失败: {e}")

    async def save(self, session_id: str, role: str, content: str):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_sync, session_id, role, content)

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
