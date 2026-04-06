#!/usr/bin/env python3
"""
网页搜索技能 - 搜索互联网内容

功能：
    1. 使用 DuckDuckGo 搜索网页
    2. 获取网页文本内容

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import asyncio
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """网页搜索技能处理器"""

    def __init__(self):
        self.name = "web_search"

    async def search(self, query: str, count=None) -> dict[str, Any]:
        """
        搜索网页

        参数:
            query: 搜索关键词
            count: 最大结果数

        返回:
            {"success": bool, "data": {"results": [...]}, "error": str or None}
        """
        # 处理 null 值（OpenAI strict 模式兼容）
        if count is None:
            count = 5

        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self._search_sync, query, count)

            bus = get_event_bus()
            await bus.publish(
                "search.completed",
                {
                    "query": query,
                    "result_count": len(results),
                },
                source="web_search",
            )

            return {
                "success": True,
                "data": {"results": results, "query": query},
                "error": None,
            }
        except Exception as e:
            logger.error(f"搜索失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    def _search_sync(self, query: str, max_results: int) -> list:
        """同步搜索"""
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in results
        ]

    async def fetch_page(self, url: str) -> dict[str, Any]:
        """
        获取网页文本内容（原生异步 HTTP）

        参数:
            url: 网页 URL

        返回:
            {"success": bool, "data": {"url": str, "text": str}, "error": str or None}
        """
        try:
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0 (Plector/1.0)"}) as client:
                response = await client.get(url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            # 移除脚本和样式
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # 截断过长内容
            if len(text) > 5000:
                text = text[:5000] + "\n... (内容已截断)"

            return {
                "success": True,
                "data": {"url": url, "text": text},
                "error": None,
            }
        except Exception as e:
            logger.error(f"获取网页失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}
