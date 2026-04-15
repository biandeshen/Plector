"""API 版本兼容性模块

职责：处理不同版本的 API 兼容，支持平滑升级
"""

from .v1_adapter import V1Adapter, V1CompatibilityLayer
from .version_detector import APIVersion, detect_version, VersionDetector

__all__ = [
    "V1Adapter",
    "V1CompatibilityLayer", 
    "APIVersion",
    "detect_version",
    "VersionDetector",
]
