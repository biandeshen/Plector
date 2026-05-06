"""MiniMax 网络搜索集成测试 — 需要 MiniMax MCP Server 运行

启动方式:
    MINIMAX_MCP_URL=http://localhost:9000 python -m pytest tests/test_minimax_search.py -v

或作为独立脚本运行:
    python tests/test_minimax_search.py
"""

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mcp_client import MCPClient

# ---- 环境检测 ----

MINIMAX_AVAILABLE = os.environ.get("MINIMAX_MCP_URL", "").startswith("http")

skip_if_no_minimax = pytest.mark.skipif(
    not MINIMAX_AVAILABLE,
    reason="需要 MiniMax MCP Server 运行（设置 MINIMAX_MCP_URL 环境变量）",
)


# ---- Fixtures ----


@pytest.fixture
def manager():
    return MCPClient("config/config.yaml")


# ---- 连接测试 ----


@pytest.mark.asyncio
@skip_if_no_minimax
async def test_connection(manager):
    """MCP 连接 — 验证 MiniMax 服务器可连接"""
    await manager.connect_all()
    assert "minimax" in manager.servers, "MiniMax 服务器未配置"


# ---- 搜索测试 ----


@pytest.mark.asyncio
@skip_if_no_minimax
async def test_web_search(manager):
    """网络搜索 — 验证搜索返回有效结果"""
    await manager.connect_all()
    result = await manager.call_tool("minimax", "web_search", {"query": "Python async await", "language": "zh-CN"})
    assert result is not None, "搜索应返回结果"


# ---- 图片理解测试 ----


@pytest.mark.asyncio
@skip_if_no_minimax
async def test_image_understanding(manager):
    """图片理解 — 验证图片分析返回有效结果"""
    await manager.connect_all()
    result = await manager.call_tool(
        "minimax",
        "understand_image",
        {"prompt": "描述这张图片", "image_source": "https://via.placeholder.com/300x200.png?text=Test+Image"},
    )
    assert result is not None, "图片理解应返回结果"


# ---- 独立运行 ----


async def main():
    print("=" * 60)
    print("MiniMax 网络搜索真实 API 测试")
    print("=" * 60)

    manager = MCPClient("config/config.yaml")

    print("[1/3] 测试 MCP 连接...")
    try:
        await manager.connect_all()
        print("[OK] MCP 配置加载成功")
    except Exception as e:
        print(f"[FAIL] 配置加载失败: {e}")
        return

    if "minimax" not in manager.servers:
        print("[FAIL] MiniMax 服务器未配置")
        return

    print("\n[2/3] 测试网络搜索...")
    try:
        result = await manager.call_tool("minimax", "web_search", {"query": "Python async await", "language": "zh-CN"})
        print("[OK] 搜索成功!")
        print("\n搜索结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[FAIL] 搜索失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n[3/3] 测试图片理解...")
    try:
        result = await manager.call_tool(
            "minimax",
            "understand_image",
            {"prompt": "描述这张图片", "image_source": "https://via.placeholder.com/300x200.png?text=Test+Image"},
        )
        print("[OK] 图片理解成功!")
        print("\n分析结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[FAIL] 图片理解失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
