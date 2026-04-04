import asyncio
from core.function_calling import ToolRegistry

async def test():
    t = ToolRegistry()
    # 工具不存在
    result = await t.execute({'function': {'name': 'nonexistent', 'arguments': '{}'}})
    print(f'工具不存在: {result}')
    assert result.get('jsonrpc') == '2.0'
    assert result.get('error', {}).get('code') == -32601

    # JSON 解析错误
    result = await t.execute({'function': {'name': 'test', 'arguments': 'invalid json'}})
    print(f'JSON 解析错误: {result}')
    assert result.get('jsonrpc') == '2.0'
    assert result.get('error', {}).get('code') == -32700

    print('JSON-RPC 2.0 格式验证通过')

asyncio.run(test())
