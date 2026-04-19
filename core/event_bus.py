"""
EventBus - v1 向后兼容模块

此文件仅用于向后兼容。所有功能现已迁移到 event_bus_v2.py。
建议使用 event_bus_v2 模块以获得最新功能。

使用方式（已弃用）:
    from core.event_bus import EventBus, get_event_bus

推荐使用:
    from core.event_bus_v2 import EventBusV2, get_event_bus_v2
"""

# 向后兼容导入 - 直接从 v2 导入
from core.event_bus_v2 import (
    Event,
    EventBusV2,
    get_event_bus,  # v1 函数名
    get_event_bus_v2,  # v2 函数名
)
from core.event_bus_v2 import (
    EventBus as EventBus,  # EventBusV2 的别名
)

__all__ = [
    "EventBus",  # v1 名称 = EventBusV2
    "EventBusV2",
    "get_event_bus",
    "get_event_bus_v2",
    "Event",
]

# 标记为已弃用
import warnings

warnings.warn("core.event_bus 已弃用，请使用 core.event_bus_v2", DeprecationWarning, stacklevel=2)
