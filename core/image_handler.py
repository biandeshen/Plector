#!/usr/bin/env python3
"""
图片处理模块 - 支持多后端的图片识别

功能：
    1. 自动发现可用的图片识别服务
    2. 支持多个 MCP Server 和 Skill
    3. 统一的图片识别接口
    4. 安全的路径和 URL 验证（SSRF 防护）

Author: Plector
Version: 2.8.0
Created: 2026-04-05
"""

import ipaddress
import logging
import re
import socket
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

__all__ = [
    "IMAGE_COMMANDS",
    "IMAGE_BACKENDS",
    "parse_image_command",
    "validate_image_source",
    "validate_image_path",
    "get_available_backends",
    "get_best_backend",
    "register_backend",
    "get_image_help",
    "clear_dns_cache",
    "get_dns_cache_stats",
]

# ============================================================
# 常量配置
# ============================================================

IMAGE_COMMANDS = {
    "分析图片": "详细描述这张图片的内容",
    "识别图片": "识别图片中的文字和内容",
    "看看这张图": "描述这张图片",
    "图片代码": "如果图片中有代码，请提取并解释代码的功能和逻辑",
    "图片架构": "分析这张架构图的设计思路和组件关系",
    "图片UI": "分析这个UI界面的设计，包括布局、配色、交互元素",
    "图片错误": "分析这张错误截图，说明错误原因和解决方案",
}

IMAGE_BACKENDS: dict[str, dict[str, Any]] = {
    "minimax": {
        "type": "mcp",
        "server": "minimax",
        "skill": None,
        "tool": "understand_image",
        "priority": 10,
        "enabled": True,
    },
}

SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
REQUEST_TIMEOUT = 5
STREAM_CHUNK_SIZE = 8192
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
DNS_CACHE_TTL = 300
DNS_CACHE_MAX_SIZE = 1000

# 全局锁
_backend_lock = threading.Lock()

# httpx 延迟导入
_httpx = None


def _get_httpx():
    global _httpx
    if _httpx is None:
        try:
            import httpx as _httpx_module

            _httpx = _httpx_module
        except ImportError as err:
            raise ImportError("缺少 httpx 依赖，请运行: pip install httpx") from err
    return _httpx


# ============================================================
# 脱敏函数
# ============================================================


def _mask_host(hostname: str) -> str:
    """脱敏主机名，仅显示首尾字符"""
    if not hostname or len(hostname) <= 4:
        return "***"
    return f"{hostname[0]}{'*' * 4}{hostname[-1]}"


# ============================================================
# DNS 缓存（简化版，10行）
# ============================================================


class _SimpleDNSCache:
    """简单的 DNS 缓存"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    def get(self, hostname: str) -> list | None:
        if hostname not in self._cache:
            return None
        entry = self._cache[hostname]
        if time.time() - entry["time"] > self._ttl:
            del self._cache[hostname]
            return None
        self._cache.move_to_end(hostname)
        return entry["ips"]

    def set(self, hostname: str, ips: list) -> None:
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[hostname] = {"ips": ips, "time": time.time()}

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict:
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
        }


_dns_cache = _SimpleDNSCache(max_size=DNS_CACHE_MAX_SIZE, ttl=DNS_CACHE_TTL)


def clear_dns_cache() -> None:
    """清空 DNS 缓存"""
    _dns_cache.clear()


def get_dns_cache_stats() -> dict:
    """获取 DNS 缓存统计"""
    return _dns_cache.stats()


# ============================================================
# DNS 解析与 IP 检查
# ============================================================


def _resolve_and_check_ip(hostname: str) -> tuple[bool, str, list]:
    """解析域名并检查是否为内网 IP"""
    # 尝试从缓存获取
    cached_ips = _dns_cache.get(hostname)
    if cached_ips is not None:
        for ip in cached_ips:
            if _is_private_ip(ip):
                return False, f"DNS 解析结果为内网 IP: {_mask_host(ip)}", []
        return True, "", cached_ips

    # 执行 DNS 解析
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        ips = list(set(r[4][0] for r in results))
    except socket.gaierror:
        try:
            results = socket.getaddrinfo(hostname, None, socket.AF_INET6)
            ips = list(set(r[4][0] for r in results))
        except socket.gaierror:
            return False, f"DNS 解析失败: {hostname}", []

    # 缓存结果
    _dns_cache.set(hostname, ips)

    # 检查内网 IP
    for ip in ips:
        if _is_private_ip(ip):
            return False, f"DNS 解析结果为内网 IP: {_mask_host(ip)}", []
    return True, "", ips


def _is_private_ip(ip_str: str) -> bool:
    """检查 IP 是否为内网/特殊 IP"""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast
    except ValueError:
        return False


# ============================================================
# HTTP 请求相关
# ============================================================


def _resolve(url: str) -> dict:
    """解析 URL，返回解析后的 URL 和主机信息"""
    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme,
        "hostname": parsed.hostname or "",
        "port": parsed.port,
        "path": parsed.path,
    }


def handle_request(method: str, url: str, **kwargs) -> Any:
    """发送 HTTP 请求"""
    httpx = _get_httpx()
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, **kwargs) as client:
            return getattr(client, method.lower())(url)
    except httpx.TimeoutException:
        return None
    except httpx.RequestError:
        return None


def get(url: str, **kwargs) -> Any:
    """发送 GET 请求"""
    return handle_request("get", url, **kwargs)


# ============================================================
# 本地文件验证（简化版，42行）
# ============================================================


def _validate_local_file(file_path: str) -> tuple[bool, str]:
    """验证本地文件路径"""
    try:
        path = Path(file_path).resolve()
        if not path.exists():
            return False, f"文件不存在: {path}"
        if not path.is_file():
            return False, f"不是文件: {path}"
        if not path.stat().st_size > 0:
            return False, f"文件为空: {path}"
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            return False, f"不支持的图片格式: {path.suffix}"
        return True, ""
    except PermissionError:
        return False, f"无权限访问: {Path(file_path).name}"
    except OSError:
        return False, f"路径无效: {file_path}"


def validate_image_path(file_path: str) -> tuple[bool, str]:
    """验证图片路径"""
    return _validate_local_file(file_path)


# ============================================================
# URL 验证 - 拆分后的模块化实现
# ============================================================


def _validate_url_basic(url: str) -> tuple[bool, str]:
    """
    验证 URL 基础信息（协议、主机名）
    拆分自 _validate_url 的基础验证部分
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL 解析失败"

    if parsed.scheme not in ("http", "https"):
        return False, "仅支持 http/https 协议"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL 缺少主机名"

    if _is_private_ip(hostname):
        return False, "禁止访问内网地址"

    ip_ok, ip_msg, safe_ips = _resolve_and_check_ip(hostname)
    if not ip_ok:
        return False, ip_msg

    return True, ""


def _check_redirect(url: str, response) -> tuple[bool, str]:
    """
    检查并处理重定向
    拆分自 _validate_url 的重定向处理部分
    """
    if response.status_code not in REDIRECT_STATUS_CODES:
        return True, ""

    location = response.headers.get("location", "")
    try:
        location_domain = urlparse(location).hostname or "未知"
    except Exception:
        location_domain = "未知"

    return False, f"禁止重定向（SSRF 防护），重定向目标: {_mask_host(location_domain)}"


def _check_http_status(url: str, response, client) -> tuple[bool, str]:
    """
    检查 HTTP 状态码
    拆分自 _validate_url 的状态码处理部分
    """
    if response.status_code < 400:
        return True, ""

    # 405 Method Not Allowed，尝试 GET
    if response.status_code == 405:
        logger.debug("HEAD 返回 405，尝试 GET")
        response = client.get(url, headers={"User-Agent": "Plector/1.0"})
        if response.status_code >= 400:
            return False, f"URL 不可达 (HTTP {response.status_code})"
        return True, ""
    else:
        return False, f"URL 不可达 (HTTP {response.status_code})"


def _validate_content_type(response) -> tuple[bool, str]:
    """
    验证 Content-Type
    拆分自 _validate_url 的类型检查部分
    """
    content_type = response.headers.get("content-type", "").lower()
    main_type = content_type.split(";")[0].strip()
    if main_type and not main_type.startswith("image/"):
        logger.warning(f"Content-Type 不是图片: {main_type}")
    return True, ""


def _stream_check_size(client, url: str) -> tuple[bool, str]:
    """流式检查文件大小"""
    total_size = 0
    try:
        with client.stream("GET", url, headers={"User-Agent": "Plector/1.0"}) as response:
            for chunk in response.iter_bytes(chunk_size=STREAM_CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    size_mb = total_size / (1024 * 1024)
                    return False, f"图片太大: {size_mb:.1f}MB（最大 20MB）"
    except Exception as e:
        logger.debug(f"流式检查失败: {e}")
    return True, ""


def _validate_content_length(response, client, url: str) -> tuple[bool, str]:
    """
    验证 Content-Length
    拆分自 _validate_url 的长度检查部分
    """
    content_length = response.headers.get("content-length")
    if not content_length:
        return _stream_check_size(client, url)

    try:
        size = int(content_length)
        if size < 0:
            logger.warning(f"Content-Length 为负数: {size}，退回到流式检查")
            return _stream_check_size(client, url)
        elif size > MAX_FILE_SIZE:
            size_mb = size / (1024 * 1024)
            return False, f"图片太大: {size_mb:.1f}MB（最大 20MB）"
    except ValueError:
        logger.warning("Content-Length 解析失败，退回到流式检查")
        return _stream_check_size(client, url)

    return True, ""


def _validate_url(url: str) -> tuple[bool, str]:
    """
    验证网络 URL（SSRF 防护）
    拆分后主函数，组合调用各验证模块
    """
    ok, msg = _validate_url_basic(url)
    if not ok:
        return False, msg

    hostname = urlparse(url).hostname
    _, _, safe_ips = _resolve_and_check_ip(hostname)

    try:
        httpx = _get_httpx()
        with httpx.Client(
            transport=_PinnedTransport(_PinnedResolver(hostname, safe_ips)),
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
        ) as client:
            response = client.head(url, headers={"User-Agent": "Plector/1.0"})

            ok, msg = _check_redirect(url, response)
            if not ok:
                return False, msg
            ok, msg = _check_http_status(url, response, client)
            if not ok:
                return False, msg
            _validate_content_type(response)
            ok, msg = _validate_content_length(response, client, url)
            return False, msg if not ok else (True, "")

    except httpx.TimeoutException:
        return False, f"URL 请求超时 ({REQUEST_TIMEOUT}秒)"
    except httpx.RequestError:
        logger.exception(f"URL 请求失败: {_mask_host(hostname)}")
        return False, "URL 请求失败"
    except Exception:
        logger.exception(f"URL 验证出错: {_mask_host(hostname)}")
        return False, "URL 验证出错"


# ============================================================
# SSRF 防护：固定 IP 解析器
# ============================================================


class _PinnedResolver:
    """固定 IP 解析器，防止 DNS 重绑定攻击"""

    def __init__(self, hostname: str, ips: list):
        self.hostname = hostname
        self.ips = ips

    def __call__(self, request):
        for ip in self.ips:
            request.url = request.url.replace(
                f"//{self.hostname}", f"//{ip}", 1
            )
            try:
                sock = socket.create_connection((ip, request.url.port or 443), timeout=5)
                sock.close()
            except OSError:
                continue
        return {"type": "http", "hostname": self.hostname, "ips": self.ips}


class _PinnedTransport:
    """固定 IP 传输层"""

    def __init__(self, resolver):
        self.resolver = resolver

    def __call__(self, request):
        return self.resolver(request)


# ============================================================
# 图片源验证
# ============================================================


def validate_image_source(source: str) -> tuple[bool, str]:
    """验证图片源（本地文件或网络 URL）"""
    if source.startswith(("http://", "https://")):
        return _validate_url(source)
    elif source.startswith(("file://", "/", "~", ".")):
        return _validate_local_file(source.lstrip("file://"))
    else:
        return _validate_local_file(source)


# ============================================================
# 图片后端管理
# ============================================================


def parse_image_command(command: str) -> str | None:
    """解析图片命令，返回标准命令"""
    command = command.strip().lower()
    for key, value in IMAGE_COMMANDS.items():
        if key in command:
            return key
    return None


def get_available_backends() -> list[str]:
    """获取可用的图片识别后端"""
    return [name for name, cfg in IMAGE_BACKENDS.items() if cfg.get("enabled", True)]


def get_best_backend() -> str | None:
    """获取最佳图片识别后端"""
    available = get_available_backends()
    if not available:
        return None
    candidates = [(name, IMAGE_BACKENDS[name]) for name in available]
    candidates.sort(key=lambda x: x[1].get("priority", 0), reverse=True)
    return candidates[0][0] if candidates else None


def register_backend(name: str, config: dict) -> None:
    """注册图片识别后端"""
    with _backend_lock:
        IMAGE_BACKENDS[name] = config


# ============================================================
# 帮助信息
# ============================================================


def get_image_help() -> str:
    """获取图片命令帮助"""
    lines = ["支持的图片命令："]
    for cmd, desc in IMAGE_COMMANDS.items():
        lines.append(f"  • {cmd}: {desc}")
    lines.append("\n支持的图片格式：")
    lines.append(f"  {', '.join(sorted(SUPPORTED_FORMATS))}")
    return "\n".join(lines)
