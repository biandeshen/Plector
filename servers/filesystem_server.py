#!/usr/bin/env python3
"""
Plector MCP Filesystem Server

功能：
    1. 读取文件
    2. 写入文件
    3. 列出目录
    4. 搜索文件
    5. 移动/重命名文件
    6. 获取文件信息

使用方式：
    python servers/filesystem_server.py [根目录]

协议：
    MCP (Model Context Protocol)
    传输：stdio
    格式：JSON-RPC 2.0

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import json
import os
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# 从命令行参数获取根目录，默认为当前目录
if len(sys.argv) > 1:
    ROOT_DIR = Path(sys.argv[1]).resolve()
    if not ROOT_DIR.exists():
        sys.exit(f"错误: 根目录不存在: {ROOT_DIR}")
    if not ROOT_DIR.is_dir():
        sys.exit(f"错误: 不是目录: {ROOT_DIR}")
else:
    ROOT_DIR = Path(".").resolve()

# 安全限制
FORBIDDEN_PATHS = ["/", "C:\\", "/etc", "/usr", "/bin", "/sbin"]


def check_safe_path(filepath: str) -> Path:
    """
    检查路径是否安全

    安全规则：
        1. 路径必须在 ROOT_DIR 内（使用 relative_to，比 startswith 更安全）
        2. 路径不能指向受保护的系统路径

    参数:
        filepath: 相对于 ROOT_DIR 的文件路径

    返回:
        解析后的绝对路径

    异常:
        PermissionError: 路径不安全
    """
    path = (ROOT_DIR / filepath).resolve()

    # 使用 relative_to 检查（比 startswith 更安全，兼容 Windows 大小写）
    try:
        path.relative_to(ROOT_DIR)
    except ValueError:
        raise PermissionError(f"路径超出根目录范围: {filepath}")

    # 确保不操作受保护路径
    resolved = str(path)
    for forbidden in FORBIDDEN_PATHS:
        if resolved == forbidden or resolved.startswith(forbidden + os.sep):
            raise PermissionError(f"禁止操作受保护路径: {resolved}")

    return path


# 创建 MCP Server
server = Server("plector-filesystem")


def _make_tool_schema(name: str, description: str,
                     required: list, optional: dict = None) -> Tool:
    """创建工具模式（函数长度限制）"""
    properties = {}
    if optional:
        properties.update(optional)

    return Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    )


def _get_read_file_schema() -> Tool:
    """获取 read_file 工具模式"""
    return _make_tool_schema(
        name="read_file",
        description="读取文件内容",
        required=["path"],
        optional={
            "path": {"type": "string", "description": "文件路径（相对于根目录）"},
            "max_lines": {"type": "integer", "description": "最大行数，默认 200", "default": 200}
        }
    )


def _get_write_file_schema() -> Tool:
    """获取 write_file 工具模式"""
    return _make_tool_schema(
        name="write_file",
        description="写入文件内容（自动创建目录）",
        required=["path", "content"],
        optional={
            "path": {"type": "string", "description": "文件路径（相对于根目录）"},
            "content": {"type": "string", "description": "文件内容"}
        }
    )


def _get_list_directory_schema() -> Tool:
    """获取 list_directory 工具模式"""
    return _make_tool_schema(
        name="list_directory",
        description="列出目录下的文件和子目录",
        required=[],
        optional={
            "path": {"type": "string", "description": "目录路径，默认 '.'", "default": "."}
        }
    )


def _get_search_files_schema() -> Tool:
    """获取 search_files 工具模式"""
    return _make_tool_schema(
        name="search_files",
        description="搜索匹配模式的文件",
        required=["pattern"],
        optional={
            "pattern": {"type": "string", "description": "搜索模式，如 '**/*.py'"}
        }
    )


def _get_move_file_schema() -> Tool:
    """获取 move_file 工具模式"""
    return _make_tool_schema(
        name="move_file",
        description="移动或重命名文件",
        required=["source", "destination"],
        optional={
            "source": {"type": "string", "description": "源路径"},
            "destination": {"type": "string", "description": "目标路径"}
        }
    )


def _get_file_info_schema() -> Tool:
    """获取 get_file_info 工具模式"""
    return _make_tool_schema(
        name="get_file_info",
        description="获取文件或目录的详细信息",
        required=["path"],
        optional={
            "path": {"type": "string", "description": "文件或目录路径"}
        }
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        _get_read_file_schema(),
        _get_write_file_schema(),
        _get_list_directory_schema(),
        _get_search_files_schema(),
        _get_move_file_schema(),
        _get_file_info_schema(),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """调用工具"""
    try:
        if name == "read_file":
            return await _read_file(arguments)
        elif name == "write_file":
            return await _write_file(arguments)
        elif name == "list_directory":
            return await _list_directory(arguments)
        elif name == "search_files":
            return await _search_files(arguments)
        elif name == "move_file":
            return await _move_file(arguments)
        elif name == "get_file_info":
            return await _get_file_info(arguments)
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]
    except PermissionError as e:
        return [TextContent(type="text", text=f"权限错误: {e}")]
    except FileNotFoundError as e:
        return [TextContent(type="text", text=f"文件不存在: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"错误: {type(e).__name__}: {e}")]


async def _read_file(arguments: dict) -> list[TextContent]:
    """读取文件"""
    filepath = arguments.get("path", "")
    max_lines = arguments.get("max_lines", 200)

    path = check_safe_path(filepath)
    if not path.exists():
        return [TextContent(type="text", text=f"文件不存在: {filepath}")]

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    if len(lines) > max_lines:
        content = "\n".join(lines[:max_lines])
        content += f"\n... (共 {len(lines)} 行，已截断到前 {max_lines} 行)"

    return [TextContent(type="text", text=content)]


async def _write_file(arguments: dict) -> list[TextContent]:
    """写入文件"""
    filepath = arguments.get("path", "")
    content = arguments.get("content", "")

    path = check_safe_path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    lines = len(content.splitlines())
    return [TextContent(type="text", text=f"已写入 {filepath} ({lines} 行)")]


async def _list_directory(arguments: dict) -> list[TextContent]:
    """列出目录"""
    dirpath = arguments.get("path", ".")

    path = check_safe_path(dirpath)
    if not path.exists():
        return [TextContent(type="text", text=f"目录不存在: {dirpath}")]
    if not path.is_dir():
        return [TextContent(type="text", text=f"不是目录: {dirpath}")]

    items = []
    for item in sorted(path.iterdir()):
        if item.is_dir():
            items.append(f"[DIR]  {item.name}/")
        else:
            size = item.stat().st_size
            items.append(f"[FILE] {item.name} ({size} bytes)")

    result = "\n".join(items) if items else "(空目录)"
    return [TextContent(type="text", text=result)]


async def _search_files(arguments: dict) -> list[TextContent]:
    """搜索文件"""
    pattern = arguments.get("pattern", "**/*")

    matches = list(ROOT_DIR.glob(pattern))
    matches = [m for m in matches if m.is_file()]
    matches.sort()

    if not matches:
        return [TextContent(type="text", text=f"未找到匹配 '{pattern}' 的文件")]

    results = []
    # 限制返回 50 个结果，避免输出过大影响 LLM 上下文
    for m in matches[:50]:
        rel = m.relative_to(ROOT_DIR)
        size = m.stat().st_size
        results.append(f"{rel} ({size} bytes)")

    if len(matches) > 50:
        results.append(f"... (共 {len(matches)} 个文件，已截断到前 50 个)")

    return [TextContent(type="text", text="\n".join(results))]


async def _move_file(arguments: dict) -> list[TextContent]:
    """移动文件"""
    source = arguments.get("source", "")
    destination = arguments.get("destination", "")

    src = check_safe_path(source)
    dst = check_safe_path(destination)

    if not src.exists():
        return [TextContent(type="text", text=f"源文件不存在: {source}")]

    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)

    return [TextContent(type="text", text=f"已移动 {source} → {destination}")]


async def _get_file_info(arguments: dict) -> list[TextContent]:
    """获取文件信息"""
    filepath = arguments.get("path", "")

    path = check_safe_path(filepath)
    if not path.exists():
        return [TextContent(type="text", text=f"路径不存在: {filepath}")]

    stat = path.stat()
    info = {
        "name": path.name,
        "path": str(path.relative_to(ROOT_DIR)),
        "type": "directory" if path.is_dir() else "file",
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }

    if path.is_dir():
        items = list(path.iterdir())
        info["children_count"] = len(items)

    return [TextContent(type="text", text=json.dumps(info, indent=2))]


async def main():
    """启动 MCP Server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
