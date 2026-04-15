#!/usr/bin/env python3
"""
网页搜索技能 - 搜索互联网内容

功能：
    1. 使用 DuckDuckGo 搜索网页
    2. 获取网页文本内容（含 SSRF 防护）

Author: Plector
Version: 1.1.0
Created: 2026-04-04
"""

import asyncio
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)

# SSRF 防护：允许访问的最大内容大小（5MB）
MAX_FETCH_SIZE = 5 * 1024 * 1024
# SSRF 防护：禁止访问的私有 IP 段
_PRIVATE_IP_PREFIXES = (
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
    "127.",
    "0.",
    "169.254.",
)


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

    def _validate_url_ssrf(self, url: str) -> tuple[bool, str]:
        """SSRF 防护：验证 URL 不指向内网地址"""
        import ipaddress
        import socket
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
        except Exception:
            return False, "URL 解析失败"

        if parsed.scheme not in ("http", "https"):
            return False, "仅支持 http/https 协议"

        hostname = parsed.hostname
        if not hostname:
            return False, "URL 缺少主机名"

        # 直接 IP 检查
        try:
            ip = ipaddress.ip_address(hostname)
            if not ip.is_global:
                return False, "禁止访问内网地址"
        except ValueError:
            pass  # 不是 IP，继续 DNS 检查

        # 字符串前缀快速检查（覆盖常见私有 IP）
        if hostname.lower() == "localhost":
            return False, "禁止访问 localhost"

        # DNS 解析后 IP 检查
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
            for addr_info in addr_infos:
                ip_str = addr_info[4][0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    if not ip.is_global:
                        return False, "域名解析到内网地址（禁止访问）"
                except ValueError:
                    continue
        except socket.gaierror:
            return False, "域名解析失败"

        return True, ""

    async def fetch_page(self, url: str) -> dict[str, Any]:
        """
        获取网页文本内容（含 SSRF 防护）

        参数:
            url: 网页 URL

        返回:
            {"success": bool, "data": {"url": str, "text": str}, "error": str or None}
        """
        # SSRF 防护：URL 验证
        url_ok, url_err = self._validate_url_ssrf(url)
        if not url_ok:
            return {"success": False, "data": None, "error": f"URL 安全检查失败: {url_err}"}

        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 (Plector/1.0)"},
                follow_redirects=False,  # 禁止跟随重定向（SSRF 防护）
            ) as client:
                response = await client.get(url)

                # 拦截重定向（SSRF 防护）
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location", "未知")
                    return {"success": False, "data": None, "error": f"禁止重定向（SSRF 防护），目标: {location}"}

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
