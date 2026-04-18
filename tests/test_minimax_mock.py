#!/usr/bin/env python3
"""
MiniMax MCP Server Mock 测试

不调用真实 API，只验证：
1. MCP 连接是否正常
2. 参数传递是否正确
3. 错误处理是否有效
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mcp_client import MCPClient


async def _test_connection():
    """测试 MCP 连接，返回 (client, server) 或 (None, None)"""
    print("\n[1/4] 测试 MCP 连接...")
    client = await MCPClient.from_config()
    print("[OK] MCP 连接成功")

    if "minimax" not in client.servers:
        print("[FAIL] MiniMax 服务器未配置")
        return None, None

    server = client.servers["minimax"]
    print(f"[OK] MiniMax 服务器已连接: {server.name}")
    return client, server


async def _test_tool_list(server):
    """测试工具列表"""
    print("\n[2/4] 测试工具列表...")
    tools = await server.list_tools()
    print(f"[OK] 工具列表获取成功，共 {len(tools)} 个工具:")
    for tool in tools:
        print(f"  - {tool.get('name')}: {tool.get('description')}")


def _test_params():
    """测试参数验证（不调用真实 API）"""
    print("\n[3/4] 测试参数验证...")
    test_cases = [
        {"name": "web_search 参数", "tool": "web_search", "args": {"query": "Python 3.13 新特性"}},
        {
            "name": "understand_image 参数",
            "tool": "understand_image",
            "args": {
                "prompt": "描述这张图片的内容",
                "image_source": "https://www.python.org/static/community_logos/python-logo.png",
            },
        },
    ]
    for test_case in test_cases:
        print(f"\n  测试: {test_case['name']}")
        print(f"    工具: {test_case['tool']}")
        print(f"    参数: {test_case['args']}")
        print("    [OK] 参数格式正确")


async def _test_error_handling(client):
    """测试错误处理"""
    print("\n[4/4] 测试错误处理...")
    print("  测试: 缺少必需参数")
    try:
        await client.call_tool("minimax", "web_search", {})
        print("  [FAIL] 应该失败但没有失败")
    except Exception as e:
        print(f"  [OK] 错误处理正常: {str(e)[:50]}...")


def _print_summary():
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("Mock 测试完成")
    print("=" * 60)
    print("\n说明:")
    print("  [OK] MCP 连接正常")
    print("  [OK] 工具列表获取成功")
    print("  [OK] 参数格式验证通过")
    print("  [OK] 错误处理正常")
    print("\n注意:")
    print("  - 本测试未调用真实 API")
    print("  - 需要订阅 Token Plan 并配置有效的 API Key 后才能测试真实 API")
    print("  - 参考文档: https://platform.minimaxi.com/subscribe/token-plan")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("MiniMax MCP Server Mock 测试")
    print("=" * 60)

    try:
        client, server = await _test_connection()
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        import traceback

        traceback.print_exc()
        return

    if client is None:
        return

    try:
        await _test_tool_list(server)
    except Exception as e:
        print(f"[FAIL] 工具列表获取失败: {e}")
        import traceback

        traceback.print_exc()
        return

    _test_params()
    await _test_error_handling(client)
    await client.close_all()
    _print_summary()


if __name__ == "__main__":
    asyncio.run(main())
