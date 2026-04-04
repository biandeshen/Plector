import pytest
import asyncio
from core.event_bus import EventBus


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
    assert received[0]["data"]["msg"] == "hello"


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
    assert e["specversion"] == "1.0"
    assert "id" in e
    assert e["source"] == "test"
    assert e["type"] == "test.format"
    assert "time" in e
    assert e["data"]["msg"] == "hello"
