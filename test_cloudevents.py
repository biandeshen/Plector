import asyncio
from core.event_bus import EventBus

async def test():
    bus = EventBus()
    received = []
    async def handler(event):
        received.append(event)
    bus.subscribe('test.event', handler)
    await bus.publish('test.event', {'msg': 'hello'}, source='test')
    await asyncio.sleep(0.1)
    assert received[0]['specversion'] == '1.0'
    assert received[0]['type'] == 'test.event'
    assert received[0]['data']['msg'] == 'hello'
    print('OK: CloudEvents 格式验证通过')

asyncio.run(test())
