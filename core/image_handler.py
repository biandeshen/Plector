#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理模块 - 支持多后端的图片识别

功能：
    1. 自动发现可用的图片识别服务
    2. 支持多个 MCP Server 和 Skill
    3. 统一的图片识别接口
    4. 安全的路径和 URL 验证

Author: Plector
Version: 2.2.0
Created: 2026-04-05
"""

import re
import logging
import ipaddress
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
# 图片命令配置
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

# ============================================================
# 图片识别后端注册表
# ============================================================

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

# 内网地址前缀（SSRF 防护）
BLOCKED_IP_PREFIXES = [
    "127.",
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
    "169.254.",
    "0.",
    "localhost",
]


# ============================================================
# 验证函数
# ============================================================

def _validate_local_file(file_path: str) -> Tuple[bool, str]:
    """
    验证本地文件

    检查项：
        1. 路径遍历防护（禁止绝对路径逃逸）
        2. 文件是否存在
        3. 是否是文件（非目录）
        4. 文件格式是否支持
        5. 文件大小是否超限
    """
    try:
        path = Path(file_path)

        # 禁止绝对路径（防止路径遍历）
        if path.is_absolute():
            # 允许用户 HOME 目录下的文件
            home = Path.home()
            try:
                path.relative_to(home)
            except ValueError:
                return False, f"禁止访问绝对路径: {file_path}\n请使用相对路径或 ~/ 开头的路径"

        # 解析为绝对路径并检查路径遍历
        abs_path = path.expanduser().resolve()

        # 检查是否包含 ..（路径遍历特征）
        if ".." in Path(file_path).parts:
            return False, f"路径包含 '..'，可能存在路径遍历风险: {file_path}"

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


def _is_blocked_ip(hostname: str) -> bool:
    """检查是否是内网地址（SSRF 防护）"""
    try:
        # 解析 IP 地址
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        # 不是 IP 地址，检查域名
        hostname_lower = hostname.lower()
        return hostname_lower in BLOCKED_IP_PREFIXES or hostname_lower == "localhost"


def _validate_url(url: str) -> Tuple[bool, str]:
    """
    验证网络 URL

    检查项：
        1. URL 格式是否正确（仅允许 http/https）
        2. 是否是内网地址（SSRF 防护）
        3. URL 是否可达（HEAD 请求）
        4. Content-Type 是否是图片
    """
    # URL 格式严格检查
    url_pattern = re.compile(
        r"^https?://"                    # 必须是 http:// 或 https://
        r"[a-zA-Z0-9]"                   # 域名首字符
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"  # 域名主体
        r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*"  # 子域名
        r"\.[a-zA-Z]{2,}"               # 顶级域名
        r"(?::\d{1,5})?"                 # 可选端口
        r"(?:/[^\s]*)?$",                # 可选路径
        re.IGNORECASE
    )

    if not url_pattern.match(url):
        return False, f"URL 格式无效（仅支持 http/https）: {url}"

    # 解析 URL 并检查内网地址
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            return False, f"URL 缺少主机名: {url}"

        if _is_blocked_ip(hostname):
            return False, f"禁止访问内网地址: {hostname}"

    except Exception as e:
        return False, f"URL 解析出错: {str(e)}"

    # HEAD 请求验证
    try:
        import httpx

        response = httpx.head(
            url,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Plector/1.0"}
        )

        # 状态码检查
        if response.status_code >= 400:
            return False, f"URL 不可达 (HTTP {response.status_code}): {url}"

        # Content-Type 检查（宽松策略）
        content_type = response.headers.get("content-type", "").lower()
        main_type = content_type.split(";")[0].strip()

        if main_type and not main_type.startswith("image/"):
            logger.warning(f"Content-Type 不是图片: {main_type}，但仍尝试处理")

        # Content-Length 检查（安全解析）
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

        return True, ""

    except ImportError:
        return False, "缺少 httpx 依赖，请运行: pip install httpx"
    except httpx.TimeoutException:
        return False, f"URL 请求超时 ({REQUEST_TIMEOUT}秒): {url}"
    except httpx.RequestError as e:
        return False, f"URL 请求失败: {str(e)}"
    except Exception as e:
        return False, f"URL 验证出错: {str(e)}"


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
    # 按优先级降序排序
    available.sort(key=lambda x: x["priority"], reverse=True)
    return available


def get_best_backend() -> Optional[Dict[str, Any]]:
    """获取最佳可用后端（按优先级）"""
    backends = get_available_backends()
    if not backends:
        return None

    # 返回优先级最高的后端
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
        server: MCP Server 名称（type=mcp 时使用）
        skill: Skill 名称（type=skill 时使用）
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
    lines.append("示例:")
    lines.append("  分析图片 ./screenshot.png")
    lines.append("  分析图片 ~/Pictures/photo.jpg")
    lines.append("  图片代码 https://example.com/code.png")
    lines.append("")
    lines.append("安全说明:")
    lines.append("  - 禁止访问绝对路径（除 ~/ 外）")
    lines.append("  - 禁止路径包含 '..'")
    lines.append("  - 禁止访问内网地址")

    return "\n".join(lines)
