#!/usr/bin/env python3
"""测试流式WebSocket"""
import asyncio, json, websockets

async def test():
    uri = 'ws://127.0.0.1:8082/ws'
    async with websockets.connect(uri, ping_timeout=30) as ws:
        await ws.send(json.dumps({'content': 'PLECtor是什么'}))
        count = 0
        tool_events = []
        for i in range(300):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(msg)
                t = data.get('type', '')
                if t == 'chunk':
                    print(data['content'], end='', flush=True)
                    count += 1
                elif t == 'toolExecuting':
                    print(f"\n[TOOL: {data.get('tool', '')}]", end='', flush=True)
                    tool_events.append(t)
                elif t == 'toolDone':
                    print(f"\n[/TOOL: {data.get('tool', '')}]", end='', flush=True)
                elif t == 'response':
                    print(f"\n\n=== Done ({count} chunks, {len(tool_events)} tools) ===")
                    break
                elif t == 'error':
                    print(f"\n[ERROR: {data.get('content', '')}]")
                    break
            except asyncio.TimeoutError:
                print(f'\ntimeout at {i}')
                break

if __name__ == '__main__':
    asyncio.run(test())
