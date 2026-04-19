"""
SSRF Guard - Security module for SSRF protection

Provides reusable SSRF validation logic for:
- web_search
- image_handler
- Any component that needs URL validation

Extracted from core/image/validator.py for reuse.
"""

import logging
import socket
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Configuration
REQUEST_TIMEOUT = 5
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

_httpx = None


def _get_httpx():
    global _httpx
    if _httpx is None:
        import httpx

        _httpx = httpx
    return _httpx


class SSRFCheckResult(NamedTuple):
    """SSRF check result"""

    safe: bool
    message: str
    safe_ips: list[str]


def is_private_ip(ip_str: str) -> bool:
    """Check if IP is private/internal"""
    import ipaddress

    try:
        ip = ipaddress.ip_address(ip_str)
        return not ip.is_global
    except ValueError:
        return ip_str.lower() == "localhost"


def mask_hostname(hostname: str) -> str:
    """Mask hostname for logging"""
    if not hostname:
        return "N/A"
    try:
        import ipaddress

        ipaddress.ip_address(hostname)
        parts = hostname.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.***.***.{parts[3]}"
    except ValueError:
        pass
    parts = hostname.split(".")
    if len(parts) >= 2:
        return f"{parts[-2]}.{parts[-1]}"
    elif len(parts) == 1:
        if len(parts[0]) <= 4:
            return parts[0]
        return parts[0][:2] + "****" + parts[0][-2:]
    return hostname


def resolve_and_check(hostname: str) -> SSRFCheckResult:
    """
    Resolve hostname and check for private IP

    Returns:
        SSRFCheckResult with safe=True if OK
    """
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
                    return SSRFCheckResult(False, "域名解析到内网地址（禁止访问）", [])

        return SSRFCheckResult(True, "", ips)
    except socket.gaierror:
        return SSRFCheckResult(False, "域名解析失败", [])
    except Exception:
        logger.exception(f"IP 检查出错: {hostname}")
        return SSRFCheckResult(False, "IP 检查出错", [])


def validate_url_scheme(url: str) -> SSRFCheckResult:
    """Validate URL scheme (http/https only)"""
    try:
        parsed = urlparse(url)
    except Exception:
        return SSRFCheckResult(False, "URL 解析失败", [])
    if parsed.scheme not in ("http", "https"):
        return SSRFCheckResult(False, "仅支持 http/https 协议", [])
    return SSRFCheckResult(True, "", [])


def validate_url_hostname(url: str) -> SSRFCheckResult:
    """Validate URL hostname presence"""
    try:
        parsed = urlparse(url)
    except Exception:
        return SSRFCheckResult(False, "URL 解析失败", [])
    hostname = parsed.hostname
    if not hostname:
        return SSRFCheckResult(False, "URL 缺少主机名", [])
    return SSRFCheckResult(True, "", [])


def validate_url_no_private_ip(hostname: str) -> SSRFCheckResult:
    """Check that hostname doesn't resolve to private IP"""
    if is_private_ip(hostname):
        return SSRFCheckResult(False, "禁止访问内网地址", [])
    return SSRFCheckResult(True, "", [])


def validate_url_dns(hostname: str) -> SSRFCheckResult:
    """Resolve and validate hostname via DNS"""
    return resolve_and_check(hostname)


def check_http_redirect(url: str, response) -> SSRFCheckResult:
    """Check for forbidden redirects (SSRF protection)"""
    if response.status_code not in REDIRECT_STATUS_CODES:
        return SSRFCheckResult(True, "", [])
    location = response.headers.get("location", "")
    try:
        loc_domain = urlparse(location).hostname or "未知"
    except Exception:
        loc_domain = "未知"
    return SSRFCheckResult(False, f"禁止重定向（SSRF 防护），重定向目标: {mask_hostname(loc_domain)}", [])


def check_http_status(url: str, response, client) -> SSRFCheckResult:
    """Check HTTP status code"""
    if response.status_code < 400:
        return SSRFCheckResult(True, "", [])
    if response.status_code == 405:
        logger.debug("HEAD 返回 405，尝试 GET")
        response = client.get(url, headers={"User-Agent": "Plector/1.0"})
        if response.status_code >= 400:
            return SSRFCheckResult(False, f"URL 不可达 (HTTP {response.status_code})", [])
        return SSRFCheckResult(True, "", [])
    return SSRFCheckResult(False, f"URL 不可达 (HTTP {response.status_code})", [])


class PinnedResolver:
    """DNS resolver that binds to safe IPs"""

    def __init__(self, hostname: str, safe_ips: list):
        self.hostname = hostname
        self.safe_ips = safe_ips

    def resolve(self, host: str, port: int = 0, family: int = 0) -> list:
        if host == self.hostname:
            results = []
            for ip_str in self.safe_ips:
                import ipaddress

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
    """HTTP Transport with pinned DNS resolution"""

    def __init__(self, resolver: PinnedResolver, **kwargs):
        self._resolver = resolver
        self._kwargs = kwargs
        self._inner = None

    @property
    def httpx(self):
        global _httpx
        if _httpx is None:
            import httpx

            _httpx = httpx
        return _httpx

    def _get_inner(self):
        if self._inner is None:
            self._inner = self.httpx.HTTPTransport(**self._kwargs)
        return self._inner

    def handle_request(self, request):
        inner = self._get_inner()
        safe_results = self._resolver.resolve(
            request.url.host, request.url.port or (443 if request.url.scheme == "https" else 80)
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


def _is_path_under(abs_path: Path, base: Path) -> bool:
    """Check if abs_path is under base directory"""
    try:
        abs_path.relative_to(base)
        return True
    except ValueError:
        return False


def validate_url_full(url: str) -> SSRFCheckResult:
    """Full URL validation with SSRF protection"""
    for check in [validate_url_scheme, validate_url_hostname]:
        result = check(url)
        if not result.safe:
            return result
    hostname = urlparse(url).hostname
    for check in [validate_url_no_private_ip, validate_url_dns]:
        result = check(hostname)
        if not result.safe:
            return result
    httpx = _get_httpx()
    resolver = PinnedResolver(hostname, result.safe_ips)
    try:
        with httpx.Client(
            transport=PinnedTransport(resolver), timeout=REQUEST_TIMEOUT, follow_redirects=False
        ) as client:
            response = client.head(url, headers={"User-Agent": "Plector/1.0"})
            for check in [check_http_redirect, check_http_status]:
                result = check(url, response, client)
                if not result.safe:
                    return result
            return SSRFCheckResult(True, "", [])
    except Exception:
        logger.exception(f"URL 验证出错: {mask_hostname(hostname)}")
        return SSRFCheckResult(False, "URL 验证出错", [])


def validate_file_path(file_path: str, allowed_paths: list[str] | None = None) -> SSRFCheckResult:
    """Validate local file path for security"""
    try:
        abs_path = Path(file_path).expanduser().resolve()
        if allowed_paths and not any(_is_path_under(abs_path, Path(p).resolve()) for p in allowed_paths):
            return SSRFCheckResult(False, f"文件不在允许的目录内: {allowed_paths}", [])
        cwd, home = Path.cwd().resolve(), Path.home().resolve()
        if not _is_path_under(abs_path, cwd) and not _is_path_under(abs_path, home):
            return SSRFCheckResult(False, "文件不在允许的目录内（仅允许当前目录或用户主目录）", [])
        if not abs_path.exists():
            return SSRFCheckResult(False, "文件不存在", [])
        if not abs_path.is_file():
            return SSRFCheckResult(False, "不是文件", [])
        suffix = abs_path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            return SSRFCheckResult(False, f"不支持的图片格式: {suffix}", [])
        file_size = abs_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return SSRFCheckResult(False, f"图片太大: {file_size / (1024 * 1024):.1f}MB（最大 20MB）", [])
        if file_size == 0:
            return SSRFCheckResult(False, "文件为空", [])
        return SSRFCheckResult(True, "", [])
    except PermissionError:
        return SSRFCheckResult(False, "没有权限访问", [])
    except Exception:
        logger.exception(f"文件验证出错: {file_path}")
        return SSRFCheckResult(False, "文件验证出错", [])
