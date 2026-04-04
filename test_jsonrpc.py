import asyncio
from core.function_calling import ToolRegistry

async def test():
    t = ToolRegistry()
    result = await t.execute({'function': {'name': 'nonexistent', 'arguments': '{}'}})
    assert result.get('jsonrpc') == '2.0'
    assert result.get('error', {}).get('code') == -32601
    print('OK: JSON-RPC 2.0 格式验证通过')

asyncio.run(test())
