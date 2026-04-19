"""
事件总线 v2 单元测试 - Plector v2.0 Phase 1
"""

import asyncio
import pytest
from core.event_bus_v2 import (
    Event,
    EventBusV2,
    WeakHandler,
    get_event_bus_v2,
)


class TestEvent:
    """测试事件类"""

    def test_event_creation(self):
        """测试事件创建"""
        event = Event(
            source="test",
            type="test.event",
            data={"key": "value"}
        )

        assert event.specversion == "1.0"
        assert event.source == "test"
        assert event.type == "test.event"
        assert event.data["key"] == "value"
        assert event.id
        assert event.time

    def test_event_auto_id(self):
        """测试自动生成 ID"""
        event1 = Event(source="test", type="test.1")
        event2 = Event(source="test", type="test.2")

        assert event1.id != event2.id


class TestWeakHandler:
    """测试弱引用包装器"""

    def test_weak_handler_basic(self):
        """测试基本功能"""
        def handler():
            return "called"

        wrapped = WeakHandler(handler)

        assert wrapped()
        assert wrapped.is_alive

    def test_weak_handler_dead(self):
        """测试死引用"""
        def handler():
            return "called"

        wrapped = WeakHandler(handler)
        del handler

        assert not wrapped.is_alive
        assert wrapped() is None  # 返回 None 而不是异常


class TestEventBusV2:
    """测试事件总线 v2"""

    @pytest.fixture
    def bus(self):
        """创建事件总线实例"""
        return EventBusV2(use_weak_ref=True, history_size=10)

    def test_subscribe_and_publish(self, bus):
        """测试订阅和发布"""
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test.event", handler)

        async def run():
            await bus.publish("test.event", {"data": "test"})

        asyncio.run(run())

        assert len(received) == 1
        assert received[0].type == "test.event"

    def test_unsubscribe(self, bus):
        """测试取消订阅"""
        def handler(event):
            pass

        bus.subscribe("test.event", handler)
        bus.unsubscribe("test.event", handler)

        assert "test.event" not in bus._subscribers

    def test_wildcard_subscription(self, bus):
        """测试通配符订阅"""
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("skill.*", handler)

        async def run():
            await bus.publish("skill.execute", {"skill": "test"})

        asyncio.run(run())

        assert len(received) == 1
        assert received[0].type == "skill.execute"

    def test_filter_function(self, bus):
        """测试事件过滤器"""
        passed = []

        async def handler(event):
            passed.append(event)

        def my_filter(event):
            return event.data.get("allowed", False)

        bus.subscribe("test.event", handler, filter_func=my_filter)

        async def run():
            await bus.publish("test.event", {"allowed": False})
            await bus.publish("test.event", {"allowed": True})

        asyncio.run(run())

        assert len(passed) == 1

    def test_history_tracking(self, bus):
        """测试历史记录"""
        async def run():
            await bus.publish("test.1", {"n": 1})
            await bus.publish("test.2", {"n": 2})
            await bus.publish("test.3", {"n": 3})

        asyncio.run(run())

        history = bus.get_history(limit=5)
        assert len(history) == 3

        # 测试过滤
        filtered = bus.get_history(event_type="test.1")
        assert len(filtered) == 1

    def test_stats(self, bus):
        """测试统计信息"""
        async def handler(event):
            pass

        bus.subscribe("test.event", handler)

        async def run():
            await bus.publish("test.event", {})

        asyncio.run(run())

        stats = bus.get_stats()

        assert stats["published"] == 1
        assert stats["delivered"] == 1
        assert stats["failed"] == 0

    def test_clear_history(self, bus):
        """测试清空历史"""
        async def run():
            await bus.publish("test", {})

        asyncio.run(run())

        bus.clear_history()

        assert len(bus.get_history()) == 0

    def test_max_subscribers_limit(self, bus):
        """测试订阅者上限"""
        async def handler(event):
            pass

        # 订阅超过上限
        for i in range(bus.MAX_SUBSCRIBERS_PER_TYPE + 10):
            bus.subscribe("test.event", handler)

        assert len(bus._subscribers["test.event"]) <= bus.MAX_SUBSCRIBERS_PER_TYPE

    def test_multiple_handlers(self, bus):
        """测试多个处理器"""
        results = {"h1": 0, "h2": 0}

        async def handler1(event):
            results["h1"] += 1

        async def handler2(event):
            results["h2"] += 1

        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)

        async def run():
            await bus.publish("test.event", {})

        asyncio.run(run())

        assert results["h1"] == 1
        assert results["h2"] == 1


@pytest.mark.asyncio
class TestEventBusV2Async:
    """异步测试"""

    async def test_async_handler(self):
        """测试异步处理器"""
        bus = EventBusV2()
        received = []

        async def async_handler(event):
            await asyncio.sleep(0.01)
            received.append(event)

        bus.subscribe("async.test", async_handler)

        await bus.publish("async.test", {"async": True})

        assert len(received) == 1

    async def test_error_handling(self):
        """测试错误处理"""
        bus = EventBusV2()

        async def failing_handler(event):
            raise ValueError("Handler failed")

        bus.subscribe("fail.test", failing_handler)

        results = await bus.publish("fail.test", {})

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Handler failed" in results[0]["error"]


class TestGetEventBusV2:
    """测试全局实例"""

    def test_singleton(self):
        """测试单例模式"""
        bus1 = get_event_bus_v2()
        bus2 = get_event_bus_v2()

        assert bus1 is bus2
