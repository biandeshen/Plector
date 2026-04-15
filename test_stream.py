#!/usr/bin/env python3
"""测试流式响应"""
import asyncio, json, websockets

async def test():
    uri = 'ws://127.0.0.1:8082/ws'
    async with websockets.connect(uri, ping_timeout=30) as ws:
        await ws.send(json.dumps({'content': 'PLECtor是什么'}))
        count = 0
        for i in range(200):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                t = data.get('type', '')
                c = data.get('content', '')
                if t == 'chunk':
                    print(c, end='', flush=True)
                    count += 1
                elif t == 'toolExecuting':
                    tool = data.get('tool', '')
                    print(f'\n[tool: {tool}]', end='', flush=True)
                elif t == 'toolDone':
                    tool = data.get('tool', '')
                    print(f'\n[/tool: {tool}]', end='', flush=True)
                elif t == 'response':
                    print()
                    print(f'=== Done ({count} chunks) ===')
                    break
            except asyncio.TimeoutError:
                print(f'\ntimeout at {i}')
                break

if __name__ == '__main__':
    asyncio.run(test())
