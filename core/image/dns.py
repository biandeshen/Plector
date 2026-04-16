"""
DNS 解析和安全检查
"""

import ipaddress
import logging
import socket
import threading
import time
from collections import OrderedDict
from typing import Optional

from .config import DNS_CACHE_TTL, DNS_CACHE_MAX_SIZE

logger = logging.getLogger(__name__)

# ============================================================
# DNS 缓存 (线程安全，LRU 策略，TTL 过期)
# ============================================================


class DNSCache:
    """DNS 解析缓存"""

    def __init__(self, ttl: int = DNS_CACHE_TTL, max_size: int = DNS_CACHE_MAX_SIZE):
        self._cache: OrderedDict[str, tuple[list[str], float]] = OrderedDict()
        self._lock = threading.Lock()
        self._ttl = ttl
        self._max_size = max_size

    def get(self, hostname: str) -> Optional[list[str]]:
        with self._lock:
            if hostname in self._cache:
                ips, timestamp = self._cache[hostname]
                if time.monotonic() - timestamp < self._ttl:
                    self._cache.move_to_end(hostname)
                    return list(ips)
                else:
                    del self._cache[hostname]
            return None

    def set(self, hostname: str, ips: list[str]):
        with self._lock:
            if hostname in self._cache:
                del self._cache[hostname]
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[hostname] = (list(ips), time.monotonic())

    def clear(self):
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


_dns_cache = DNSCache()


# ============================================================
# DNS 解析器 (防 DNS Rebinding)
# ============================================================


class PinnedResolver:
    """绑定 IP 的 DNS Resolver"""

    def __init__(self, hostname: str, safe_ips: list[str]):
        self.hostname = hostname
        self.safe_ips = safe_ips

    def resolve(self, host: str, port: int = 0, family: int = 0) -> list:
        if host == self.hostname:
            results = []
            for ip_str in self.safe_ips:
                try:
                    ip = ipaddress.ip_address(ip_str)
                    if ip.version == 4:
                        results.append((socket.AF_INET, ip_str, port or 443))
                    else:
                        results.append((socket.AF_INET6, ip_str, port or 443))
                except ValueError:
                    continue
            if results:
                return results
        return socket.getaddrinfo(host, port, family)


class PinnedTransport:
    """绑定 IP 的 HTTP Transport"""

    def __init__(self, resolver: PinnedResolver, **kwargs):
        self._resolver = resolver
        self._kwargs = kwargs
        self._inner = None
        self._httpx = None

    @property
    def httpx(self):
        if self._httpx is None:
            import httpx
            self._httpx = httpx
        return self._httpx

    def _get_inner(self):
        if self._inner is None:
            self._inner = self.httpx.HTTPTransport(**self._kwargs)
        return self._inner

    def handle_request(self, request):
        inner = self._get_inner()
        safe_results = self._resolver.resolve(
            request.url.host,
            request.url.port or (443 if request.url.scheme == "https" else 80)
        )

        if not safe_results:
            raise self.httpx.ConnectError("没有可用的安全 IP 地址")

        _, safe_ip, _ = safe_results[0]
        original_host = request.url.host
        new_url = request.url.copy_with(host=safe_ip)

        request = self.httpx.Request(
            method=request.method,
            url=new_url,
            headers={**dict(request.headers), "Host": original_host},
            content=request.content,
        )

        return inner.handle_request(request)

    def close(self):
        if self._inner:
            self._inner.close()


# ============================================================
# 公共函数
# ============================================================


def is_private_ip(ip_str: str) -> bool:
    """检查是否为内网/私有 IP 地址"""
    try:
        ip = ipaddress.ip_address(ip_str)
        return not ip.is_global
    except ValueError:
        return ip_str.lower() == "localhost"


def resolve_and_check(hostname: str) -> tuple[bool, str, list[str]]:
    """
    解析域名为 IP 并检查是否为内网地址
    返回: (是否安全, 错误消息, IP列表)
    """
    cached_ips = _dns_cache.get(hostname)
    if cached_ips is not None:
        for ip_str in cached_ips:
            if is_private_ip(ip_str):
                return False, "域名解析到内网地址（禁止访问）", []
        return True, "", cached_ips

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
        ips = []
        seen = set()

        for addr_info in addr_infos:
            ip_str = addr_info[4][0]
            if ip_str not in seen:
                seen.add(ip_str)
                ips.append(ip_str)
                if is_private_ip(ip_str):
                    _dns_cache.set(hostname, ips)
                    return False, "域名解析到内网地址（禁止访问）", []

        _dns_cache.set(hostname, ips)
        return True, "", ips

    except socket.gaierror:
        return False, "域名解析失败", []
    except Exception:
        logger.exception(f"IP 检查出错: {hostname}")
        return False, "IP 检查出错", []


def get_dns_cache() -> DNSCache:
    """获取全局 DNS 缓存实例"""
    return _dns_cache


def mask_hostname(hostname: str) -> str:
    """
    脱敏主机名，保护敏感信息

    示例：
        example.com → example.com
        127.0.0.1 → 127.***.***.1
        internal.corp.example.com → example.com
    """
    if not hostname:
        return "N/A"

    # IP 地址脱敏
    try:
        ipaddress.ip_address(hostname)
        parts = hostname.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.***.***.{parts[3]}"
        return "***"
    except ValueError:
        pass

    # 域名脱敏：只显示顶级和二级域名
    parts = hostname.split(".")
    if len(parts) >= 2:
        return f"{parts[-2]}.{parts[-1]}"
    elif len(parts) == 1:
        if len(parts[0]) <= 4:
            return parts[0]
        return parts[0][:2] + "****" + parts[0][-2:]
    return hostname
