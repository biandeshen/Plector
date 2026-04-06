#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 MiniMax 图片理解功能"""

import asyncio
import json
from core.mcp_manager import MCPManager


async def test_understand_image():
    """测试图片理解"""
    manager = MCPManager()
    await manager.load_config()

    print("=" * 60)
    print("测试：图片理解")
    print("=" * 60)

    result = await manager.call_tool('minimax', 'understand_image', {
        'prompt': '描述这张图片的内容',
        'image_source': 'https://www.python.org/static/community_logos/python-logo.png'
    })

    print(f"\n图片分析结果：\n{json.dumps(result, indent=2, ensure_ascii=False)}")

    print("\n" + "=" * 60)
    print("[OK] 图片理解测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_understand_image())
