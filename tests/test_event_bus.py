import pytest
import asyncio
from core.event_bus_v2 import EventBusV2 as EventBus


@pytest.mark.asyncio
async def test_publish_subscribe():
    bus = EventBus()
    received = []
    async def handler(event):
        received.append(event)
    bus.subscribe("test.event", handler)
    await bus.publish("test.event", {"msg": "hello"}, source="test")
    await asyncio.sleep(0.1)
    assert len(received) == 1
    assert received[0].data["msg"] == "hello"  # Event 对象使用属性访问


@pytest.mark.asyncio
async def test_wildcard_subscribe():
    bus = EventBus()
    received = []
    async def handler(event):
        received.append(event)
    bus.subscribe("skill.*", handler)
    await bus.publish("skill.failed", {"skill": "test"}, source="test")
    await asyncio.sleep(0.1)
    assert len(received) == 1


@pytest.mark.asyncio
async def test_cloudevents_format():
    bus = EventBus()
    received = []
    async def handler(event):
        received.append(event)
    bus.subscribe("test.format", handler)
    await bus.publish("test.format", {"msg": "hello"}, source="test")
    await asyncio.sleep(0.1)
    e = received[0]
    assert e.specversion == "1.0"  # Event 对象使用属性访问
    assert e.id
    assert e.source == "test"
    assert e.type == "test.format"
    assert e.time
    assert e.data["msg"] == "hello"


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    received = []
    async def handler(event):
        received.append(event)
    bus.subscribe("unsub.test", handler)
    bus.unsubscribe("unsub.test", handler)
    await bus.publish("unsub.test", {}, source="test")
    await asyncio.sleep(0.1)
    assert len(received) == 0


@pytest.mark.asyncio
async def test_multiple_handlers():
    bus = EventBus()
    r1, r2 = [], []
    async def h1(e): r1.append(e)
    async def h2(e): r2.append(e)
    bus.subscribe("multi.*", h1)
    bus.subscribe("multi.*", h2)
    await bus.publish("multi.test", {}, source="test")
    await asyncio.sleep(0.1)
    assert len(r1) == 1
    assert len(r2) == 1


@pytest.mark.asyncio
async def test_handler_exception_no_crash():
    """handler 异常不应阻塞其他 handler"""
    bus = EventBus()
    ok = []
    async def bad(e): raise RuntimeError("bad")
    async def good(e): ok.append(e)
    bus.subscribe("exc.*", bad)
    bus.subscribe("exc.*", good)
    await bus.publish("exc.test", {}, source="test")
    await asyncio.sleep(0.1)
    assert len(ok) == 1
