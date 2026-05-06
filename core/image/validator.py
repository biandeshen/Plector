# mypy: ignore-errors
"""
图片路径和 URL 验证

SSRF 防护逻辑已提取到 core.security.ssrf_guard 模块
"""

import logging

from core.security.ssrf_guard import (
    PinnedResolver,
    PinnedTransport,
    _get_httpx,
    check_http_redirect,
    check_http_status,
    mask_hostname,
    validate_file_path,
    validate_url_dns,
    validate_url_hostname,
    validate_url_no_private_ip,
    validate_url_scheme,
)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 5


def validate_image_path(file_path: str) -> tuple[bool, str]:
    """
    验证本地图片文件路径

    返回: (是否有效, 错误消息)
    """
    result = validate_file_path(file_path)
    return result.safe, result.message


def _http_check_url(url: str, hostname: str, safe_ips: list) -> tuple[bool, str]:
    """通过 HTTP 请求验证 URL 可达性和内容类型"""
    httpx = _get_httpx()
    resolver = PinnedResolver(hostname, safe_ips)

    with httpx.Client(
        transport=PinnedTransport(resolver),
        timeout=REQUEST_TIMEOUT,
        follow_redirects=False,
    ) as client:
        response = client.head(url, headers={"User-Agent": "Plector/1.0"})

        # 检查重定向
        result = check_http_redirect(url, response)
        if not result.safe:
            return False, result.message

        # 检查响应状态
        result = check_http_status(url, response, client)
        if not result.safe:
            return False, result.message

        # 检查 Content-Type
        content_type = response.headers.get("content-type", "").lower()
        main_type = content_type.split(";")[0].strip()
        if main_type and not main_type.startswith("image/"):
            logger.warning(f"Content-Type 不是图片: {main_type}")

    return True, ""


def validate_image_url(url: str) -> tuple[bool, str]:
    """验证网络图片 URL（SSRF 防护）"""
    # Scheme 验证
    result = validate_url_scheme(url)
    if not result.safe:
        return False, result.message

    # Hostname 验证
    result = validate_url_hostname(url)
    if not result.safe:
        return False, result.message

    hostname = None
    if result.safe:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        hostname = parsed.hostname
    if not hostname:
        return False, "URL 缺少主机名"

    # 私有 IP 检查
    result = validate_url_no_private_ip(hostname)
    if not result.safe:
        return False, result.message

    # DNS 解析检查
    result = validate_url_dns(hostname)
    if not result.safe:
        return False, result.message

    safe_ips = result.safe_ips

    try:
        return _http_check_url(url, hostname, safe_ips)
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
