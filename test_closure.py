import asyncio
from core.agent_loop import AgentLoop
from core.event_bus import get_event_bus

async def test():
    # 初始化 AgentLoop（会创建 ClosureEngine，订阅事件）
    agent = AgentLoop()

    # 发布 test.failed 事件
    bus = get_event_bus()
    await bus.publish('test.failed', {'error': 'syntax error in main.py'}, source='e2e_test')

    # 等待异步处理
    await asyncio.sleep(2)
    print('事件已发布，检查 data/errors/ 目录')

asyncio.run(test())
