"""
图片路径和 URL 验证
"""

import logging
from pathlib import Path
from urllib.parse import urlparse

from .config import SUPPORTED_FORMATS, MAX_FILE_SIZE, REQUEST_TIMEOUT, REDIRECT_STATUS_CODES
from .dns import resolve_and_check, PinnedResolver, PinnedTransport, mask_hostname

logger = logging.getLogger(__name__)

_httpx = None


def _get_httpx():
    global _httpx
    if _httpx is None:
        import httpx as h
        _httpx = h
    return _httpx


def validate_image_path(file_path: str) -> tuple[bool, str]:
    """
    验证本地图片文件路径
    
    返回: (是否有效, 错误消息)
    """
    try:
        expanded = Path(file_path).expanduser()
        abs_path = expanded.resolve()

        # 检查是否在允许的目录内
        cwd = Path.cwd().resolve()
        home = Path.home().resolve()

        try:
            abs_path.relative_to(cwd)
        except ValueError:
            try:
                abs_path.relative_to(home)
            except ValueError:
                return False, "文件不在允许的目录内（仅允许当前目录或用户主目录）"

        # 检查文件是否存在
        if not abs_path.exists():
            return False, "文件不存在"

        if not abs_path.is_file():
            return False, "不是文件"

        # 检查格式
        suffix = abs_path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            return False, f"不支持的图片格式: {suffix}"

        # 检查大小
        file_size = abs_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return False, f"图片太大: {file_size / (1024 * 1024):.1f}MB（最大 20MB）"

        if file_size == 0:
            return False, "文件为空"

        return True, ""

    except PermissionError:
        return False, "没有权限访问"
    except Exception:
        logger.exception(f"文件验证出错: {mask_hostname(file_path)}")
        return False, "文件验证出错"


def validate_image_url(url: str) -> tuple[bool, str]:
    """
    验证网络图片 URL（SSRF 防护）
    
    返回: (是否有效, 错误消息)
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL 解析失败"

    # 协议检查
    if parsed.scheme not in ("http", "https"):
        return False, "仅支持 http/https 协议"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL 缺少主机名"

    # 内网 IP 检查
    from .dns import is_private_ip
    if is_private_ip(hostname):
        return False, "禁止访问内网地址"

    # DNS 解析和 IP 检查
    ip_ok, ip_msg, safe_ips = resolve_and_check(hostname)
    if not ip_ok:
        return False, ip_msg

    try:
        httpx = _get_httpx()
        resolver = PinnedResolver(hostname, safe_ips)

        with httpx.Client(
            transport=PinnedTransport(resolver),
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
        ) as client:
            response = client.head(url, headers={"User-Agent": "Plector/1.0"})

            # 检查重定向
            if response.status_code in REDIRECT_STATUS_CODES:
                location = response.headers.get("location", "")
                try:
                    loc_domain = urlparse(location).hostname or "未知"
                except Exception:
                    loc_domain = "未知"
                return False, f"禁止重定向（SSRF 防护），重定向目标: {mask_hostname(loc_domain)}"

            # 检查响应状态
            if response.status_code >= 400:
                if response.status_code == 405:
                    # HEAD 不支持，尝试 GET
                    logger.debug("HEAD 返回 405，尝试 GET")
                    response = client.get(url, headers={"User-Agent": "Plector/1.0"})
                    if response.status_code >= 400:
                        return False, f"URL 不可达 (HTTP {response.status_code})"
                else:
                    return False, f"URL 不可达 (HTTP {response.status_code})"

            # 检查 Content-Type
            content_type = response.headers.get("content-type", "").lower()
            main_type = content_type.split(";")[0].strip()
            if main_type and not main_type.startswith("image/"):
                logger.warning(f"Content-Type 不是图片: {main_type}")

        return True, ""

    except Exception:
        logger.exception(f"URL 验证出错: {mask_hostname(hostname)}")
        return False, "URL 验证出错"


def validate_image_source(source: str) -> tuple[bool, str]:
    """
    统一验证图片来源（本地路径或 URL）
    
    返回: (是否有效, 错误消息)
    """
    source = source.strip()

    if not source:
        return False, "图片来源为空"

    # 判断是 URL 还是本地路径
    if source.startswith(("http://", "https://", "ftp://")):
        return validate_image_url(source)
    else:
        return validate_image_path(source)
