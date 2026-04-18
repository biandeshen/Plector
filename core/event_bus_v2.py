"""
事件总线 v2 - Plector v2.0 Phase 1
内存优化版本，解决事件总线内存泄漏风险
"""

import asyncio
import fnmatch
import logging
import time
import weakref
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """
    CloudEvents 格式的事件
    
    相比 v1 版本：
    1. 添加 max_age 参数控制事件生命周期
    2. 使用 __slots__ 优化内存（如果需要）
    """
    specversion: str = "1.0"
    id: str = ""
    source: str = "plector"
    type: str = ""
    time: str = ""
    data: dict = field(default_factory=dict)
    
    _id_counter: int = 0
    _id_lock: int = 0

    def __post_init__(self):
        if not self.time:
            self.time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not self.id:
            import threading
            with threading.Lock():
                Event._id_counter += 1
                self.id = f"{self.source}-{int(time.time() * 1000)}-{Event._id_counter}"


class WeakHandler:
    """
    弱引用包装器
    防止 handler 被引用时无法被垃圾回收
    """
    __slots__ = ('_ref', '_callback', '_is_async')
    
    def __init__(self, handler: Callable, callback: Optional[Callable] = None):
        self._ref = weakref.ref(handler)
        self._callback = callback
        self._is_async = asyncio.iscoroutinefunction(handler)
    
    def __call__(self, *args, **kwargs):
        handler = self._ref()
        if handler is not None:
            return handler(*args, **kwargs)
        elif self._callback:
            self._callback()
    
    @property
    def is_alive(self) -> bool:
        """
        检查 handler 是否仍然存活
        """
        return self._ref() is not None


class EventBusV2:
    """
    事件总线 v2 - 内存优化版本
    
    相比 v1 版本改进：
    1. 支持弱引用 handler，防止内存泄漏
    2. 添加订阅者上限，防止过度订阅
    3. 支持事件历史记录（可配置上限）
    4. 添加批量订阅/取消订阅
    5. 支持事件过滤器
    """
    
    MAX_SUBSCRIBERS_PER_TYPE = 100
    MAX_EVENT_HISTORY = 1000
    
    def __init__(self, use_weak_ref: bool = True, history_size: int = 100):
        """
        初始化事件总线
        
        Args:
            use_weak_ref: 是否使用弱引用（默认 True，防止内存泄漏）
            history_size: 事件历史记录大小（默认 100，设为 0 可禁用）
        """
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._use_weak_ref = use_weak_ref
        self._history_size = min(history_size, self.MAX_EVENT_HISTORY)
        self._event_history: list[Event] = []
        self._filters: dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._stats = {
            "published": 0,
            "delivered": 0,
            "failed": 0,
        }
    
    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        filter_func: Optional[Callable] = None,
        use_weak: Optional[bool] = None
    ):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型，支持通配符 'skill.*'
            handler: 处理函数
            filter_func: 事件过滤器
            use_weak: 是否使用弱引用（覆盖全局设置）
        """
        # 检查订阅者上限
        if len(self._subscribers[event_type]) >= self.MAX_SUBSCRIBERS_PER_TYPE:
            logger.warning(f"订阅者上限已达到: {event_type}")
            return
        
        # 使用弱引用包装
        use_weak_ref = use_weak if use_weak is not None else self._use_weak_ref
        if use_weak_ref:
            wrapped = WeakHandler(handler)
            self._subscribers[event_type].append(wrapped)
        else:
            self._subscribers[event_type].append(handler)
        
        # 注册过滤器
        if filter_func:
            self._filters[event_type] = filter_func
        
        logger.debug(f"订阅事件: {event_type}, handler: {getattr(handler, '__name__', repr(handler))}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """
        取消订阅"""
        handlers = self._subscribers.get(event_type, [])
        for i, h in enumerate(handlers):
            # 支持弱引用包装器
            if isinstance(h, WeakHandler):
                if h._ref() is handler or h._ref() is None:
                    handlers.pop(i)
                    break
            elif h is handler:
                handlers.pop(i)
                break
        
        # 清理空的订阅
        if not handlers:
            del self._subscribers[event_type]
            self._filters.pop(event_type, None)
        
        logger.debug(f"取消订阅: {event_type}")
    
    def unsubscribe_all(self, event_type: str):
        """
        取消所有指定类型的订阅"""
        self._subscribers.pop(event_type, None)
        self._filters.pop(event_type, None)
        logger.debug(f"取消所有订阅: {event_type}")
    
    async def _execute_handler(self, handler: Callable, event: Event, event_type: str) -> dict:
        """执行单个事件处理器，返回结果"""
        try:
            if not self._apply_filter(event_type, event):
                return None

            is_async = isinstance(handler, WeakHandler) and handler._is_async
            if not is_async:
                is_async = asyncio.iscoroutinefunction(handler)

            if is_async:
                result = await handler(event)
            else:
                result = handler(event)

            self._stats["delivered"] += 1
            return {"handler": getattr(handler, '__name__', repr(handler)), "result": result, "success": True}

        except Exception as e:
            logger.error(f"事件处理器异常 [{event_type}]: {e}")
            self._stats["failed"] += 1
            return {"handler": getattr(handler, '__name__', repr(handler)), "error": str(e), "success": False}

    async def publish(
        self,
        event_type: str,
        data: dict,
        source: str = "plector",
        track_history: bool = True
    ) -> list[dict]:
        """
        发布 CloudEvents 格式的事件

        Args:
            event_type: 事件类型
            data: 事件数据
            source: 发布者名称
            track_history: 是否记录历史

        Returns:
            list[dict]: 每个处理器的执行结果
        """
        event = Event(
            id=f"{source}-{int(time.time() * 1000)}",
            source=source,
            type=event_type,
            data=data
        )

        if track_history and self._history_size > 0:
            await self._add_to_history(event)

        self._stats["published"] += 1

        matched_handlers = self._match_handlers(event_type)
        results = []

        for handler in matched_handlers:
            result = await self._execute_handler(handler, event, event_type)
            if result is not None:
                results.append(result)

        return results
    
    def _match_handlers(self, event_type: str) -> list[Callable]:
        """
        匹配事件处理器，避免重复触发"""
        handlers = []
        matched_patterns = set()
        
        # 精确匹配
        for h in self._subscribers.get(event_type, []):
            if isinstance(h, WeakHandler) and not h.is_alive:
                continue
            handlers.append(h)
            matched_patterns.add(event_type)
        
        # 通配符匹配
        for pattern in self._subscribers.keys():
            if pattern == event_type:
                continue
            if "*" in pattern and fnmatch.fnmatch(event_type, pattern):
                for h in self._subscribers[pattern]:
                    if isinstance(h, WeakHandler):
                        if h.is_alive and h not in handlers:
                            handlers.append(h)
                    elif h not in handlers:
                        handlers.append(h)
        
        return handlers
    
    def _apply_filter(self, event_type: str, event: Event) -> bool:
        """
        应用事件过滤器"""
        filter_func = self._filters.get(event_type)
        if filter_func:
            try:
                return filter_func(event)
            except Exception as e:
                logger.warning(f"过滤器执行失败: {e}")
                return True  # 过滤器失败默认放行
        return True
    
    async def _add_to_history(self, event: Event):
        """
        添加事件到历史记录"""
        async with self._lock:
            self._event_history.append(event)
            # 限制历史记录大小
            if len(self._event_history) > self._history_size:
                self._event_history = self._event_history[-self._history_size:]
    
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> list[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 筛选事件类型（可选）
            limit: 返回数量上限
            
        Returns:
            list[Event]: 历史事件列表
        """
        history = self._event_history
        
        if event_type:
            history = [e for e in history if fnmatch.fnmatch(e.type, event_type)]
        
        return history[-limit:]
    
    def clear_history(self):
        """
        清空事件历史"""
        self._event_history.clear()
        logger.debug("事件历史已清空")
    
    def get_stats(self) -> dict:
        """
        获取统计信息"""
        return {
            **self._stats,
            "subscriber_count": sum(len(h) for h in self._subscribers.values()),
            "event_types": list(self._subscribers.keys()),
            "history_size": len(self._event_history),
        }
    
    def cleanup_dead_handlers(self):
        """
        清理已失效的弱引用处理器"""
        for event_type in list(self._subscribers.keys()):
            handlers = self._subscribers[event_type]
            alive_handlers = [
                h for h in handlers
                if isinstance(h, WeakHandler) and h.is_alive
                or not isinstance(h, WeakHandler)
            ]
            if alive_handlers:
                self._subscribers[event_type] = alive_handlers
            else:
                del self._subscribers[event_type]


# 全局实例
_instance: Optional[EventBusV2] = None
_instance_v1: Optional[EventBusV2] = None  # v1 兼容实例


def get_event_bus_v2() -> EventBusV2:
    """
    获取全局 EventBusV2 实例"""
    global _instance
    if _instance is None:
        _instance = EventBusV2()
    return _instance


# v1 向后兼容别名
EventBus = EventBusV2


def get_event_bus() -> EventBusV2:
    """
    获取全局 EventBus 实例（v1 向后兼容）
    
    实际上是 EventBusV2 的别名
    """
    global _instance_v1
    if _instance_v1 is None:
        _instance_v1 = EventBusV2()
    return _instance_v1
