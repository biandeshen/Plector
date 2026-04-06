#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理模块 - 支持多后端的图片识别

功能：
    1. 自动发现可用的图片识别服务
    2. 支持多个 MCP Server 和 Skill
    3. 统一的图片识别接口
    4. 安全的路径和 URL 验证（SSRF 防护）

Author: Plector
Version: 2.5.0
Created: 2026-04-05
"""

import re
import logging
import ipaddress
import socket
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

__all__ = [
    "IMAGE_COMMANDS",
    "IMAGE_BACKENDS",
    "parse_image_command",
    "validate_image_source",
    "get_available_backends",
    "get_best_backend",
    "register_backend",
    "get_image_help",
]

# ============================================================
# 常量配置
# ============================================================

# 图片命令配置
IMAGE_COMMANDS = {
    "分析图片": "详细描述这张图片的内容",
    "识别图片": "识别图片中的文字和内容",
    "看看这张图": "描述这张图片",
    "图片代码": "如果图片中有代码，请提取并解释代码的功能和逻辑",
    "图片架构": "分析这张架构图的设计思路和组件关系",
    "图片UI": "分析这个UI界面的设计，包括布局、配色、交互元素",
    "图片错误": "分析这张错误截图，说明错误原因和解决方案",
}

# 图片识别后端注册表
IMAGE_BACKENDS: Dict[str, Dict[str, Any]] = {
    "minimax": {
        "type": "mcp",
        "server": "minimax",
        "skill": None,
        "tool": "understand_image",
        "priority": 10,
        "enabled": True,
    },
}

# 支持的图片格式
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# 图片 MIME 类型
IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
    "image/bmp",
}

# 最大文件大小 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024

# 请求超时（秒）
REQUEST_TIMEOUT = 5

# 流式下载检查大小限制（字节）
STREAM_CHECK_SIZE = 1024 * 1024  # 1MB

# 流式下载块大小
STREAM_CHUNK_SIZE = 8192

# HTTP 重定向状态码
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}

# DNS 缓存配置
DNS_CACHE_TTL = 300       # 缓存有效期（秒）
DNS_CACHE_MAX_SIZE = 1000  # 最大缓存条目数

# httpx 延迟导入标记
_httpx = None


def _get_httpx():
    """延迟导入 httpx"""
    global _httpx
    if _httpx is None:
        try:
            import httpx as _httpx_module
            _httpx = _httpx_module
        except ImportError:
            raise ImportError("缺少 httpx 依赖，请运行: pip install httpx")
    return _httpx


# ============================================================
# DNS 缓存
# ============================================================

class _DNSCache:
    """DNS 解析缓存（带 TTL 和容量限制）"""

    def __init__(self, ttl: int = DNS_CACHE_TTL, max_size: int = DNS_CACHE_MAX_SIZE):
        self._cache: Dict[str, Tuple[List[str], float]] = {}
        self._ttl = ttl
        self._max_size = max_size

    def get(self, hostname: str) -> Optional[List[str]]:
        """获取缓存的 IP 列表"""
        if hostname in self._cache:
            ips, timestamp = self._cache[hostname]
            if time.time() - timestamp < self._ttl:
                return ips
            else:
                # 过期，删除
                del self._cache[hostname]
        return None

    def set(self, hostname: str, ips: List[str]):
        """设置缓存"""
        # 容量检查，删除最旧的条目
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[hostname] = (ips, time.time())

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


# 全局 DNS 缓存实例
_dns_cache = _DNSCache()


# ============================================================
# 路径验证函数
# ============================================================

def _validate_local_file(file_path: str) -> Tuple[bool, str]:
    """
    验证本地文件

    安全策略：
        1. 先解析为绝对路径
        2. 检查是否在允许的目录内（工作目录或用户 HOME）
        3. 检查文件属性
    """
    try:
        # 先 expanduser 处理 ~/ 路径
        expanded = Path(file_path).expanduser()

        # 解析为绝对路径（这一步会解析所有 .. 和符号链接）
        abs_path = expanded.resolve()

        # 获取允许的根目录
        cwd = Path.cwd().resolve()
        home = Path.home().resolve()

        # 检查是否在允许的目录内
        try:
            abs_path.relative_to(cwd)
        except ValueError:
            try:
                abs_path.relative_to(home)
            except ValueError:
                return False, (
                    f"文件不在允许的目录内: {file_path}\n"
                    f"允许的目录: 当前目录或用户主目录"
                )

        # 存在性检查
        if not abs_path.exists():
            return False, f"文件不存在: {file_path}"

        # 类型检查
        if not abs_path.is_file():
            return False, f"不是文件: {file_path}"

        # 格式检查
        suffix = abs_path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            return False, f"不支持的图片格式: {suffix}\n支持: {', '.join(sorted(SUPPORTED_FORMATS))}"

        # 大小检查
        file_size = abs_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            return False, f"图片太大: {size_mb:.1f}MB（最大 20MB）"

        if file_size == 0:
            return False, "文件为空"

        return True, ""

    except PermissionError:
        return False, f"没有权限访问: {file_path}"
    except Exception as e:
        return False, f"文件验证出错: {str(e)}"


# ============================================================
# URL 验证函数
# ============================================================

def _is_private_ip(ip_str: str) -> bool:
    """
    检查是否是内网/私有 IP 地址

    支持 IPv4 和 IPv6
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_reserved or
            ip.is_multicast
        )
    except ValueError:
        # 不是 IP 地址，检查域名
        hostname_lower = ip_str.lower()
        if hostname_lower == "localhost":
            return True
        return False


def _resolve_and_check_ip(hostname: str) -> Tuple[bool, str]:
    """
    解析域名为 IP 并检查是否为内网地址

    用于防御 DNS Rebinding 攻击
    使用缓存提高性能
    """
    # 检查缓存
    cached_ips = _dns_cache.get(hostname)
    if cached_ips is not None:
        # 使用缓存的 IP 列表
        for ip_str in cached_ips:
            if _is_private_ip(ip_str):
                return False, f"域名解析到内网地址: {hostname}"
        return True, ""

    try:
        # 解析域名为 IP 地址列表
        addr_infos = socket.getaddrinfo(hostname, None)
        ips = []

        for addr_info in addr_infos:
            # addr_info 格式: (family, type, proto, canonname, sockaddr)
            ip_str = addr_info[4][0]
            ips.append(ip_str)

            if _is_private_ip(ip_str):
                # 缓存结果（即使是内网地址也缓存，避免重复解析）
                _dns_cache.set(hostname, ips)
                return False, f"域名解析到内网地址: {hostname} -> {ip_str}"

        # 缓存结果
        _dns_cache.set(hostname, ips)
        return True, ""

    except socket.gaierror as e:
        return False, f"域名解析失败: {hostname}"
    except Exception as e:
        return False, f"IP 检查出错"


def _validate_url(url: str) -> Tuple[bool, str]:
    """
    验证网络 URL

    安全策略：
        1. 使用 urlparse 解析（而非正则）
        2. 检查协议（仅 http/https）
        3. 检查内网地址（SSRF 防护）
        4. DNS 解析检查（防 DNS Rebinding）
        5. 禁止重定向（防重定向绕过）
        6. HEAD 请求验证可达性
        7. 流式检查大小（当 HEAD 不提供 Content-Length 时）
    """
    # 解析 URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"URL 解析失败"

    # 协议检查
    if parsed.scheme not in ("http", "https"):
        return False, f"仅支持 http/https 协议"

    # 主机名检查
    hostname = parsed.hostname
    if not hostname:
        return False, f"URL 缺少主机名"

    # SSRF 防护：检查主机名是否是内网 IP
    if _is_private_ip(hostname):
        return False, f"禁止访问内网地址"

    # DNS Rebinding 防护：解析域名并检查 IP
    ip_ok, ip_msg = _resolve_and_check_ip(hostname)
    if not ip_ok:
        return False, ip_msg

    # HTTP 请求验证
    try:
        httpx = _get_httpx()

        # 禁止重定向（防 SSRF 重定向绕过）
        response = httpx.head(
            url,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,  # 显式禁止重定向
            headers={"User-Agent": "Plector/1.0"}
        )

        # 检查是否是重定向响应
        if response.status_code in REDIRECT_STATUS_CODES:
            location = response.headers.get("location", "")
            # 仅显示域名，不显示完整路径（防信息泄露）
            try:
                location_parsed = urlparse(location)
                location_domain = location_parsed.hostname or "未知"
            except Exception:
                location_domain = "未知"
            return False, (
                f"禁止重定向（SSRF 防护）\n"
                f"重定向目标域名: {location_domain}"
            )

        # 状态码检查
        if response.status_code >= 400:
            return False, f"URL 不可达 (HTTP {response.status_code})"

        # Content-Type 检查（宽松策略）
        content_type = response.headers.get("content-type", "").lower()
        main_type = content_type.split(";")[0].strip()
        if main_type and not main_type.startswith("image/"):
            logger.warning(f"Content-Type 不是图片: {main_type}，但仍尝试处理")

        # Content-Length 检查
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size < 0:
                    logger.warning(f"Content-Length 为负数: {size}，忽略检查")
                elif size > MAX_FILE_SIZE:
                    size_mb = size / (1024 * 1024)
                    return False, f"图片太大: {size_mb:.1f}MB（最大 20MB）"
            except ValueError:
                logger.warning(f"Content-Length 解析失败: {content_length}，忽略检查")
        else:
            # HEAD 不提供 Content-Length 时，用 GET 流式检查
            logger.debug("HEAD 未返回 Content-Length，使用 GET 流式检查")
            try:
                with httpx.stream("GET", url, timeout=REQUEST_TIMEOUT) as resp:
                    total = 0
                    for chunk in resp.iter_bytes(chunk_size=STREAM_CHUNK_SIZE):
                        total += len(chunk)
                        if total > STREAM_CHECK_SIZE:
                            return False, f"图片超过大小限制（流式检查已下载 {total / 1024:.0f}KB）"
                logger.debug(f"流式检查完成，下载了 {total} 字节")
            except Exception as e:
                logger.warning(f"流式检查失败，跳过大小检查")

        return True, ""

    except httpx.TimeoutException:
        return False, f"URL 请求超时 ({REQUEST_TIMEOUT}秒)"
    except httpx.RequestError as e:
        return False, f"URL 请求失败"
    except Exception as e:
        return False, f"URL 验证出错"


# ============================================================
# 统一验证入口
# ============================================================

def validate_image_source(image_source: str) -> Tuple[bool, str]:
    """
    验证图片来源（统一入口）

    参数:
        image_source: 图片路径或 URL

    返回:
        (is_valid, error_message)
    """
    # 输入验证
    if not isinstance(image_source, str):
        return False, f"图片路径必须是字符串，收到: {type(image_source).__name__}"

    image_source = image_source.strip()
    if not image_source:
        return False, "图片路径不能为空"

    # URL 检测（严格匹配 http:// 或 https:// 开头）
    if re.match(r"^https?://", image_source, re.IGNORECASE):
        return _validate_url(image_source)
    else:
        return _validate_local_file(image_source)


# ============================================================
# 命令解析函数
# ============================================================

def parse_image_command(user_input: Any) -> Optional[Dict[str, Any]]:
    """
    解析图片命令

    参数:
        user_input: 用户输入

    返回:
        {"command": "分析图片", "prompt": "...", "image_path": "..."}
        或 None
    """
    # 输入验证
    if not isinstance(user_input, str):
        return None

    user_input = user_input.strip()
    if not user_input:
        return None

    for prefix, prompt in IMAGE_COMMANDS.items():
        if user_input.startswith(prefix):
            image_path = user_input[len(prefix):].strip()
            if image_path:
                return {
                    "command": prefix,
                    "prompt": prompt,
                    "image_path": image_path,
                }
    return None


def validate_image_path(image_path: str) -> Tuple[bool, str]:
    """对外接口，保持兼容"""
    return validate_image_source(image_path)


# ============================================================
# 后端管理函数
# ============================================================

def get_available_backends() -> List[Dict[str, Any]]:
    """获取可用的图片识别后端列表"""
    available = []
    for name, config in IMAGE_BACKENDS.items():
        if config.get("enabled", True):
            available.append({
                "name": name,
                "type": config["type"],
                "priority": config.get("priority", 0),
            })
    available.sort(key=lambda x: x["priority"], reverse=True)
    return available


def get_best_backend() -> Optional[Dict[str, Any]]:
    """获取最佳可用后端（按优先级）"""
    backends = get_available_backends()
    if not backends:
        return None
    best_name = backends[0]["name"]
    return {"name": best_name, **IMAGE_BACKENDS[best_name]}


def register_backend(
    name: str,
    backend_type: str,
    server: Optional[str] = None,
    skill: Optional[str] = None,
    tool: str = "",
    priority: int = 0,
):
    """
    注册新的图片识别后端

    参数:
        name: 后端名称
        backend_type: "mcp" 或 "skill"
        server: MCP Server 名称（type=mcp 时必须指定）
        skill: Skill 名称（type=skill 时必须指定）
        tool: 工具名称
        priority: 优先级（越大越优先）
    """
    if backend_type not in ("mcp", "skill"):
        raise ValueError(f"不支持的后端类型: {backend_type}（仅支持 mcp/skill）")

    if backend_type == "mcp" and not server:
        raise ValueError("MCP 类型后端必须指定 server")

    if backend_type == "skill" and not skill:
        raise ValueError("Skill 类型后端必须指定 skill")

    IMAGE_BACKENDS[name] = {
        "type": backend_type,
        "server": server,
        "skill": skill,
        "tool": tool,
        "priority": priority,
        "enabled": True,
    }
    logger.info(f"注册图片识别后端: {name} ({backend_type})")


def clear_dns_cache():
    """清空 DNS 缓存"""
    _dns_cache.clear()
    logger.info("DNS 缓存已清空")


def get_dns_cache_stats() -> Dict[str, Any]:
    """获取 DNS 缓存统计"""
    return {
        "size": _dns_cache.size(),
        "max_size": DNS_CACHE_MAX_SIZE,
        "ttl": DNS_CACHE_TTL,
    }


# ============================================================
# 帮助信息
# ============================================================

def get_image_help() -> str:
    """获取图片命令帮助信息"""
    lines = ["图片识别命令：", ""]

    for prefix, description in IMAGE_COMMANDS.items():
        lines.append(f"  {prefix} <图片路径或URL>")
        lines.append(f"    {description}")
        lines.append("")

    lines.append(f"支持格式: {', '.join(sorted(SUPPORTED_FORMATS))}")
    lines.append("最大大小: 20MB")
    lines.append("URL 超时: 5秒")
    lines.append("")

    backends = get_available_backends()
    if backends:
        lines.append("可用后端：")
        for b in backends:
            lines.append(f"  - {b['name']} ({b['type']}, 优先级: {b['priority']})")
        lines.append("")

    lines.append("其他命令：")
    lines.append("  分析图片 后端 - 查看可用后端")
    lines.append("  分析图片 帮助 - 查看帮助")
    lines.append("")

    lines.append("安全说明:")
    lines.append("  - 仅允许访问工作目录或用户主目录")
    lines.append("  - 禁止访问内网地址（IPv4 + IPv6）")
    lines.append("  - 禁止 HTTP 重定向（SSRF 防护）")
    lines.append("  - DNS 解析后检查 IP（防 DNS Rebinding）")
    lines.append("  - DNS 缓存（TTL 5分钟，最大 1000 条）")

    return "\n".join(lines)
