import asyncio
from collections import defaultdict
from typing import Callable, Dict, List

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: dict):
        for handler in self._subscribers.get(event_type, []):
            asyncio.create_task(handler(payload))
        for pattern in list(self._subscribers.keys()):
            if pattern.endswith('*') and event_type.startswith(pattern[:-1]):
                for handler in self._subscribers[pattern]:
                    asyncio.create_task(handler(payload))

# 全局单例
_instance = None

def get_event_bus() -> EventBus:
    global _instance
    if _instance is None:
        _instance = EventBus()
    return _instance
