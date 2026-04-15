"""测试 MiniMax 网络搜索真实 API"""
import asyncio
import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows UTF-8 输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

from core.mcp_client import MCPClient


async def test_connection(client: MCPClient) -> bool:
    """测试 MCP 连接"""
    print("[1/3] 测试 MCP 连接...")
    try:
        await client.connect_all()
        print("[OK] MCP 连接成功")
        return True
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        return False


async def test_web_search(client: MCPClient) -> bool:
    """测试网络搜索"""
    print("\n[2/3] 测试网络搜索...")
    try:
        result = await client.call_tool(
            'minimax',
            'web_search',
            {
                'query': 'Python async await',
                'language': 'zh-CN'
            }
        )
        print("[OK] 搜索成功！")
        print("\n搜索结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        print(f"[FAIL] 搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_image_understanding(client: MCPClient) -> bool:
    """测试图片理解"""
    print("\n[3/3] 测试图片理解...")
    try:
        result = await client.call_tool(
            'minimax',
            'understand_image',
            {
                'prompt': '描述这张图片',
                'image_source': 'https://via.placeholder.com/300x200.png?text=Test+Image'
            }
        )
        print("[OK] 图片理解成功！")
        print("\n分析结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        print(f"[FAIL] 图片理解失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 60)
    print("MiniMax 网络搜索真实 API 测试")
    print("=" * 60)

    client = await MCPClient.from_config()

    # 测试连接
    if not await test_connection(client):
        return

    # 检查 minimax 服务器
    if 'minimax' not in client.servers:
        print("[FAIL] MiniMax 服务器未配置")
        return

    # 测试网络搜索
    await test_web_search(client)

    # 测试图片理解
    await test_image_understanding(client)

    # 清理
    await client.close_all()

    # 总结
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
