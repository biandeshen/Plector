#!/usr/bin/env python3
"""WebSocket流式测试"""
import asyncio, json, websockets

async def test():
    uri = 'ws://127.0.0.1:8082/ws'
    async with websockets.connect(uri, ping_timeout=30) as ws:
        await ws.send(json.dumps({'content': 'Hello'}))
        count = 0
        for i in range(300):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                t = data.get('type', '')
                if t == 'chunk':
                    print(data.get('content', ''), end='', flush=True)
                    count += 1
                elif t == 'response':
                    print()
                    print('Done, chunks:', count)
                    break
                elif t == 'toolExecuting':
                    print('[tool:' + data.get('tool', '') + ']', end='', flush=True)
                elif t == 'error':
                    print('ERROR:', data.get('content', '')[:100])
                    break
            except asyncio.TimeoutError:
                print('timeout at', i)
                break

if __name__ == '__main__':
    asyncio.run(test())
