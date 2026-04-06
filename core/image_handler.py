#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理模块 - 支持多后端的图片识别

功能：
    1. 自动发现可用的图片识别服务
    2. 支持多个 MCP Server 和 Skill
    3. 统一的图片识别接口

扩展方式：
    只需在 IMAGE_BACKENDS 中注册新服务

Author: Plector
Version: 2.0.0
Created: 2026-04-05
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

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
    # 格式: "名称": {"type": "mcp"|"skill", "server": "xxx", "tool": "xxx"}
    "minimax": {
        "type": "mcp",
        "server": "minimax",
        "tool": "understand_image",
        "priority": 10,  # 优先级，数字越大越优先
        "enabled": True,
    },
    # 未来扩展示例：
    # "openai_vision": {
    #     "type": "skill",
    #     "skill": "vision",
    #     "tool": "analyze_image",
    #     "priority": 20,
    #     "enabled": True,
    # },
    # "local_ocr": {
    #     "type": "skill",
    #     "skill": "ocr",
    #     "tool": "recognize",
    #     "priority": 5,
    #     "enabled": True,
    # },
}

# 支持的图片格式
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


# ============================================================
# 核心函数
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


def validate_image_path(image_path: str) -> tuple[bool, str]:
    """
    验证图片路径

    返回:
        (is_valid, error_message)
    """
    # 网络 URL 直接通过
    if image_path.startswith(("http://", "https://")):
        return True, ""

    # 本地文件检查
    path = Path(image_path)

    if not path.exists():
        return False, f"文件不存在: {image_path}"

    if not path.is_file():
        return False, f"不是文件: {image_path}"

    # 检查文件格式
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        return False, f"不支持的图片格式: {suffix}\n支持格式: {', '.join(SUPPORTED_FORMATS)}"

    # 检查文件大小（最大 20MB）
    file_size = path.stat().st_size
    max_size = 20 * 1024 * 1024
    if file_size > max_size:
        size_mb = file_size / (1024 * 1024)
        return False, f"图片太大: {size_mb:.1f}MB（最大 20MB）"

    return True, ""


def get_available_backends() -> List[Dict[str, Any]]:
    """
    获取可用的图片识别后端列表

    返回:
        [{"name": "minimax", "type": "mcp", "priority": 10}, ...]
    """
    available = []
    for name, config in IMAGE_BACKENDS.items():
        if config.get("enabled", True):
            available.append({
                "name": name,
                "type": config["type"],
                "priority": config.get("priority", 0),
            })

    # 按优先级排序
    available.sort(key=lambda x: x["priority"], reverse=True)
    return available


def get_best_backend() -> Optional[Dict[str, Any]]:
    """
    获取最佳可用后端

    返回:
        {"name": "minimax", "type": "mcp", "server": "minimax", "tool": "understand_image"}
        或 None
    """
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
    """
    注册新的图片识别后端

    参数:
        name: 后端名称
        backend_type: "mcp" 或 "skill"
        server_or_skill: MCP Server 名称或 Skill 名称
        tool: 工具名称
        priority: 优先级（越大越优先）

    示例:
        register_backend(
            name="openai_vision",
            backend_type="skill",
            server_or_skill="vision",
            tool="analyze_image",
            priority=20,
        )
    """
    IMAGE_BACKENDS[name] = {
        "type": backend_type,
        "server" if backend_type == "mcp" else "skill": server_or_skill,
        "tool": tool,
        "priority": priority,
        "enabled": True,
    }
    logger.info(f"注册图片识别后端: {name}")


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

    # 显示可用后端
    backends = get_available_backends()
    if backends:
        lines.append("可用后端：")
        for b in backends:
            lines.append(f"  - {b['name']} ({b['type']})")
        lines.append("")

    lines.append("示例:")
    lines.append("  分析图片 ./screenshot.png")
    lines.append("  图片代码 https://example.com/code.png")

    return "\n".join(lines)
