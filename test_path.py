import asyncio
from core.mcp_manager import MCPManager

async def test():
    m = MCPManager()
    await m.load_config()
    tools = m.get_all_tools()
    
    # 统计
    servers = {}
    for t in tools:
        s = t['server']
        servers[s] = servers.get(s, 0) + 1
    
    # 输出
    print(f"总计 {len(tools)} 个工具:")
    for s, c in sorted(servers.items()):
        print(f"  - {s}: {c}")

if __name__ == '__main__':
    asyncio.run(test())
