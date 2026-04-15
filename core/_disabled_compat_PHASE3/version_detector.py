"""API 版本检测器

职责：检测请求的 API 版本，提供版本信息
"""

from enum import Enum
from typing import Optional, Callable
from dataclasses import dataclass


class APIVersion(Enum):
    """API 版本枚举"""
    V1 = "v1"
    V2 = "v2"
    AUTO = "auto"


@dataclass
class VersionInfo:
    """版本信息"""
    version: APIVersion
    raw: str
    major: int
    minor: int
    patch: int


class VersionDetector:
    """API 版本检测器"""
    
    def __init__(self):
        self._handlers = {
            APIVersion.V1: [],
            APIVersion.V2: [],
        }
    
    def register_handler(self, version: APIVersion, handler: Callable) -> None:
        """注册版本处理函数"""
        self._handlers[version].append(handler)
    
    def detect_from_headers(self, headers: dict) -> APIVersion:
        """从请求头检测版本"""
        # 检查 X-API-Version 头
        api_version = headers.get("X-API-Version") or headers.get("API-Version")
        if api_version:
            return self._parse_version(api_version)
        
        # 检查 Accept 头
        accept = headers.get("Accept", "")
        if "application/vnd.plector.v1" in accept:
            return APIVersion.V1
        if "application/vnd.plector.v2" in accept:
            return APIVersion.V2
        
        # 默认为 V2
        return APIVersion.V2
    
    def detect_from_path(self, path: str) -> APIVersion:
        """从路径检测版本"""
        if "/v1/" in path or path.startswith("/v1"):
            return APIVersion.V1
        if "/v2/" in path or path.startswith("/v2"):
            return APIVersion.V2
        return APIVersion.V2
    
    def parse_version_string(self, version_str: str) -> Optional[VersionInfo]:
        """解析版本字符串"""
        import re
        
        # 支持格式: v1, v1.0, v1.0.0
        pattern = r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?"
        match = re.match(pattern, version_str)
        
        if not match:
            return None
        
        major = int(match.group(1))
        minor = int(match.group(2) or 0)
        patch = int(match.group(3) or 0)
        
        # 确定版本类型
        if major == 1:
            version = APIVersion.V1
        elif major == 2:
            version = APIVersion.V2
        else:
            version = APIVersion.AUTO
        
        return VersionInfo(
            version=version,
            raw=version_str,
            major=major,
            minor=minor,
            patch=patch,
        )
    
    def _parse_version(self, version_str: str) -> APIVersion:
        """解析版本字符串"""
        info = self.parse_version_string(version_str)
        if info:
            return info.version
        return APIVersion.V2


def detect_version(headers: Optional[dict] = None, path: Optional[str] = None) -> APIVersion:
    """便捷的版本检测函数"""
    detector = VersionDetector()
    
    if headers:
        return detector.detect_from_headers(headers)
    if path:
        return detector.detect_from_path(path)
    
    return APIVersion.V2
