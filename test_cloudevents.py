import asyncio
from core.event_bus import EventBus

async def test():
    bus = EventBus()
    received = []
    async def handler(event):
        received.append(event)
    bus.subscribe('health.degraded', handler)
    await bus.publish('health.degraded', {'cpu': 85.0, 'memory': 90.0}, source='e2e_test')
    await asyncio.sleep(0.5)
    e = received[0]
    print(f'specversion: {e["specversion"]}')
    print(f'id: {e["id"]}')
    print(f'source: {e["source"]}')
    print(f'type: {e["type"]}')
    print(f'time: {e["time"]}')
    print(f'data: {e["data"]}')
    assert e['specversion'] == '1.0'
    print('CloudEvents 格式验证通过')

asyncio.run(test())
