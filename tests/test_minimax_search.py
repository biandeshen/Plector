#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 MiniMax 网络搜索功能"""

import asyncio
import json
from core.mcp_manager import MCPManager


async def test_web_search():
    """测试网络搜索"""
    manager = MCPManager()
    await manager.load_config()

    print("=" * 60)
    print("测试：网络搜索")
    print("=" * 60)

    result = await manager.call_tool('minimax', 'web_search', {
        'query': 'Python 3.13 新特性'
    })

    print(f"\n搜索结果：\n{json.dumps(result, indent=2, ensure_ascii=False)}")

    print("\n" + "=" * 60)
    print("[OK] 网络搜索测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_web_search())
