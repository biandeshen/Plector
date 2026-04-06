#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理模块 - 支持多后端的图片识别

功能：
    1. 自动发现可用的图片识别服务
    2. 支持多个 MCP Server 和 Skill
    3. 统一的图片识别接口
    4. 工具验证（非白名单）

Author: Plector
Version: 2.1.0
Created: 2026-04-05
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

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

IMAGE_BACKENDS = {
    "minimax": {
        "type": "mcp",
        "server": "minimax",
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


# ============================================================
# 验证函数
# ============================================================

def _validate_local_file(file_path: str) -> Tuple[bool, str]:
    """
    验证本地文件

    检查项：
        1. 文件是否存在
        2. 是否是文件（非目录）
        3. 文件格式是否支持
        4. 文件大小是否超限
    """
    try:
        path = Path(file_path)

        # 存在性检查
        if not path.exists():
            return False, f"文件不存在: {file_path}"

        # 类型检查
        if not path.is_file():
            return False, f"不是文件: {file_path}"

        # 格式检查
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            return False, f"不支持的图片格式: {suffix}\n支持: {', '.join(SUPPORTED_FORMATS)}"

        # 大小检查
        file_size = path.stat().st_size
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


def _validate_url(url: str) -> Tuple[bool, str]:
    """
    验证网络 URL

    检查项：
        1. URL 格式是否正确
        2. URL 是否可达（HEAD 请求）
        3. Content-Type 是否是图片
    """
    # URL 格式检查
    url_pattern = re.compile(
        r"^https?://"
        r"[^\s/$.?#].[^\s]*$",
        re.IGNORECASE
    )
    if not url_pattern.match(url):
        return False, f"URL 格式无效: {url}"

    # HEAD 请求验证
    try:
        import httpx

        response = httpx.head(
            url,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Plector/1.0"}
        )

        # 状态码检查
        if response.status_code >= 400:
            return False, f"URL 不可达 (HTTP {response.status_code}): {url}"

        # Content-Type 检查
        content_type = response.headers.get("content-type", "").lower()
        main_type = content_type.split(";")[0].strip()

        if main_type not in IMAGE_MIME_TYPES:
            # 有些服务器不返回正确的 Content-Type，只警告不阻止
            if main_type and not main_type.startswith("image/"):
                logger.warning(f"Content-Type 不是图片: {main_type}，但仍尝试处理")

        # Content-Length 检查
        content_length = response.headers.get("content-length")
        if content_length:
            size = int(content_length)
            if size > MAX_FILE_SIZE:
                size_mb = size / (1024 * 1024)
                return False, f"图片太大: {size_mb:.1f}MB（最大 20MB）"

        return True, ""

    except httpx.TimeoutException:
        return False, f"URL 请求超时: {url}"
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
    if image_source.startswith(("http://", "https://")):
        return _validate_url(image_source)
    else:
        return _validate_local_file(image_source)


# ============================================================
# 命令解析函数
# ============================================================

def parse_image_command(user_input: str) -> Optional[Dict[str, Any]]:
    """
    解析图片命令

    参数:
        user_input: 用户输入

    返回:
        {"command": "分析图片", "prompt": "...", "image_path": "..."}
        或 None
    """
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
    """获取最佳可用后端"""
    for name, config in IMAGE_BACKENDS.items():
        if config.get("enabled", True):
            return {"name": name, **config}
    return None


def register_backend(
    name: str,
    backend_type: str,
    server_or_skill: str,
    tool: str,
    priority: int = 0,
):
    """注册新的图片识别后端"""
    IMAGE_BACKENDS[name] = {
        "type": backend_type,
        "server" if backend_type == "mcp" else "skill": server_or_skill,
        "tool": tool,
        "priority": priority,
        "enabled": True,
    }
    logger.info(f"注册图片识别后端: {name}")


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

    lines.append(f"支持格式: {', '.join(SUPPORTED_FORMATS)}")
    lines.append("最大大小: 20MB")
    lines.append("")

    backends = get_available_backends()
    if backends:
        lines.append("可用后端：")
        for b in backends:
            lines.append(f"  - {b['name']} ({b['type']})")
        lines.append("")

    lines.append("其他命令：")
    lines.append("  分析图片 后端 - 查看可用后端")
    lines.append("  分析图片 帮助 - 查看帮助")
    lines.append("")
    lines.append("示例:")
    lines.append("  分析图片 ./screenshot.png")
    lines.append("  分析图片 ~/Pictures/photo.jpg")
    lines.append("  图片代码 https://example.com/code.png")

    return "\n".join(lines)
