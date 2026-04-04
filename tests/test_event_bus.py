import pytest
import asyncio
from core.event_bus import EventBus

@pytest.mark.asyncio
async def test_publish_subscribe():
    bus = EventBus()
    received = []
    async def handler(payload):
        received.append(payload)
    bus.subscribe("test.event", handler)
    await bus.publish("test.event", {"msg": "hello"})
    await asyncio.sleep(0.1)
    assert len(received) == 1
    assert received[0]["msg"] == "hello"
