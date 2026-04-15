import asyncio
import fnmatch
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable

logger = logging.getLogger(__name__)


class EventBus:
    """
    异步事件总线，对齐 CloudEvents 格式

    CloudEvents 格式：
    {
        "specversion": "1.0",
        "id": "唯一ID",
        "source": "发布者",
        "type": "event.type",
        "time": "ISO 8601",
        "data": {...}
    }
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        """注册事件处理器，支持通配符 'skill.*'"""
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, data: dict, source: str = "plector"):
        """
        发布 CloudEvents 格式的事件

        参数:
            event_type: 事件类型，如 "health.degraded"
            data: 事件数据
            source: 发布者名称
        """
        event = {
            "specversion": "1.0",
            "id": str(uuid.uuid4()),
            "source": source,
            "type": event_type,
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data": data,
        }
        matched_handlers = self._match_handlers(event_type)
        for handler in matched_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"事件处理器异常 [{event_type}]: {e}")

    def _match_handlers(self, event_type: str) -> list[Callable]:
        """匹配事件处理器，避免重复触发"""
        handlers = []
        # 精确匹配
        handlers.extend(self._subscribers.get(event_type, []))
        # 通配符匹配（排除已精确匹配的）
        for pattern in self._subscribers.keys():
            if "*" in pattern and fnmatch.fnmatch(event_type, pattern):
                for h in self._subscribers[pattern]:
                    if h not in self._subscribers.get(event_type, []):
                        handlers.append(h)
        return handlers


# 全局单例
_instance = None


def get_event_bus() -> EventBus:
    """获取全局 EventBus 单例"""
    global _instance
    if _instance is None:
        _instance = EventBus()
    return _instance
