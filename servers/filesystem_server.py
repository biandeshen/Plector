#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plector MCP Filesystem Server（纯 Python 实现，不依赖 mcp SDK）

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
    JSON-RPC 2.0 over stdio

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import json
import os
import sys
from pathlib import Path


# 从命令行参数获取根目录
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
    """检查路径是否安全"""
    path = (ROOT_DIR / filepath).resolve()
    try:
        path.relative_to(ROOT_DIR)
    except ValueError:
        raise PermissionError(f"路径超出根目录范围: {filepath}")
    resolved = str(path)
    for forbidden in FORBIDDEN_PATHS:
        if resolved == forbidden or resolved.startswith(forbidden + os.sep):
            raise PermissionError(f"禁止操作受保护路径: {resolved}")
    return path


# 工具定义
TOOLS = [
    {
        "name": "read_file",
        "description": "读取文件内容",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "max_lines": {"type": "integer", "description": "最大行数"},
            },
            "required": ["path", "max_lines"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_file",
        "description": "写入文件内容（自动创建目录）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "文件内容"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_directory",
        "description": "列出目录下的文件和子目录",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_files",
        "description": "搜索匹配模式的文件",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "搜索模式，如 '**/*.py'"},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_file",
        "description": "移动或重命名文件",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "源路径"},
                "destination": {"type": "string", "description": "目标路径"},
            },
            "required": ["source", "destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_file_info",
        "description": "获取文件或目录的详细信息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件或目录路径"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
]


def handle_read_file(args: dict) -> str:
    """读取文件"""
    filepath = args.get("path")
    max_lines = args.get("max_lines")
    # 处理 null 值（OpenAI strict 模式兼容）
    if max_lines is None:
        max_lines = 200
    path = check_safe_path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if len(lines) > max_lines:
        content = "\n".join(lines[:max_lines])
        content += f"\n... (共 {len(lines)} 行，已截断到前 {max_lines} 行)"
    return content


def handle_write_file(args: dict) -> str:
    """写入文件"""
    filepath = args.get("path", "")
    content = args.get("content", "")
    path = check_safe_path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    lines = len(content.splitlines())
    return f"已写入 {filepath} ({lines} 行)"


def handle_list_directory(args: dict) -> str:
    """列出目录"""
    dirpath = args.get("path")
    # 处理 null 值（OpenAI strict 模式兼容）
    if dirpath is None:
        dirpath = "."
    path = check_safe_path(dirpath)
    if not path.exists():
        raise FileNotFoundError(f"目录不存在: {dirpath}")
    if not path.is_dir():
        raise ValueError(f"不是目录: {dirpath}")
    items = []
    for item in sorted(path.iterdir()):
        if item.is_dir():
            items.append(f"[DIR]  {item.name}/")
        else:
            size = item.stat().st_size
            items.append(f"[FILE] {item.name} ({size} bytes)")
    return "\n".join(items) if items else "(空目录)"


def handle_search_files(args: dict) -> str:
    """搜索文件"""
    pattern = args.get("pattern", "**/*")
    matches = [m for m in ROOT_DIR.glob(pattern) if m.is_file()]
    matches.sort()
    if not matches:
        return f"未找到匹配 '{pattern}' 的文件"
    results = []
    # 限制返回 50 个结果，避免输出过大影响 LLM 上下文
    for m in matches[:50]:
        rel = m.relative_to(ROOT_DIR)
        size = m.stat().st_size
        results.append(f"{rel} ({size} bytes)")
    if len(matches) > 50:
        results.append(f"... (共 {len(matches)} 个文件，已截断到前 50 个)")
    return "\n".join(results)


def handle_move_file(args: dict) -> str:
    """移动文件"""
    source = args.get("source", "")
    destination = args.get("destination", "")
    src = check_safe_path(source)
    dst = check_safe_path(destination)
    if not src.exists():
        raise FileNotFoundError(f"源文件不存在: {source}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    return f"已移动 {source} -> {destination}"


def handle_get_file_info(args: dict) -> str:
    """获取文件信息"""
    filepath = args.get("path", "")
    path = check_safe_path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"路径不存在: {filepath}")
    stat = path.stat()
    info = {
        "name": path.name,
        "path": str(path.relative_to(ROOT_DIR)),
        "type": "directory" if path.is_dir() else "file",
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }
    if path.is_dir():
        info["children_count"] = len(list(path.iterdir()))
    return json.dumps(info, indent=2)


# 工具处理器映射
TOOL_HANDLERS = {
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "list_directory": handle_list_directory,
    "search_files": handle_search_files,
    "move_file": handle_move_file,
    "get_file_info": handle_get_file_info,
}


def _initialize(req_id) -> dict:
    """处理 initialize 请求"""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "plector-filesystem", "version": "1.0.0"},
        },
    }


def _list_tools(req_id) -> dict:
    """处理 tools/list 请求"""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": TOOLS},
    }


def _call_tool(req_id, tool_name: str, arguments: dict) -> dict:
    """处理 tools/call 请求"""
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"未知工具: {tool_name}"},
        }
    try:
        result_text = handler(arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": result_text}]},
        }
    except PermissionError as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": f"权限错误: {e}"}]},
        }
    except FileNotFoundError as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": f"文件不存在: {e}"}]},
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": f"错误: {type(e).__name__}: {e}"}]},
        }


def handle_request(request: dict) -> dict:
    """处理 JSON-RPC 2.0 请求"""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return _initialize(req_id)

    elif method == "notifications/initialized":
        return None  # 通知，不需要响应

    elif method == "tools/list":
        return _list_tools(req_id)

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        return _call_tool(req_id, tool_name, arguments)

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"未知方法: {method}"},
        }


def main():
    """主循环：从 stdin 读取请求，处理后写入 stdout"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            response = handle_request(request)

            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "JSON 解析失败"},
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
        except Exception:
            break


if __name__ == "__main__":
    main()
