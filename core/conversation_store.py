import asyncio
import logging
import sqlite3

logger = logging.getLogger(__name__)


class ConversationStore:
    """对话持久化存储"""

    def __init__(self, db_path: str = "data/plector.db"):
        self.db_path = db_path

    def _save_sync(self, session_id: str, role: str, content: str):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"保存对话失败: {e}")

    async def save(self, session_id: str, role: str, content: str):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_sync, session_id, role, content)
