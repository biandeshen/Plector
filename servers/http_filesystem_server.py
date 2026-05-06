#!/usr/bin/env python3
"""
Plector HTTP+SSE MCP Filesystem Server

功能：
    通过 HTTP+SSE 协议提供文件系统工具

启动方式：
    python servers/http_filesystem_server.py [根目录] [--port 3000]

访问：
    SSE: http://localhost:3000/sse
    消息: http://localhost:3000/message

Author: Plector
Version: 1.0.0
Created: 2026-04-05
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse

# 从命令行参数获取根目录
if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
    ROOT_DIR = Path(sys.argv[1]).resolve()
    if not ROOT_DIR.exists():
        sys.exit(f"错误: 根目录不存在: {ROOT_DIR}")
else:
    ROOT_DIR = Path(".").resolve()

# 安全限制
FORBIDDEN_PATHS = ["/", "C:\\", "/etc", "/usr", "/bin", "/sbin"]


def check_safe_path(filepath):
    """检查路径是否安全"""
    path = (ROOT_DIR / filepath).resolve()
    try:
        path.relative_to(ROOT_DIR)
    except ValueError as err:
        raise PermissionError(f"路径超出根目录范围: {filepath}") from err
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
]


def handle_read_file(args):
    filepath = args.get("path", "")
    max_lines = args.get("max_lines", 200)
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


def handle_write_file(args):
    filepath = args.get("path", "")
    content = args.get("content", "")
    path = check_safe_path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"已写入 {filepath}"


def handle_list_directory(args):
    dirpath = args.get("path", ".")
    if dirpath is None:
        dirpath = "."
    path = check_safe_path(dirpath)
    if not path.exists():
        raise FileNotFoundError(f"目录不存在: {dirpath}")
    items = []
    for item in sorted(path.iterdir()):
        if item.is_dir():
            items.append(f"[DIR]  {item.name}/")
        else:
            items.append(f"[FILE] {item.name} ({item.stat().st_size} bytes)")
    return "\n".join(items) if items else "(空目录)"


TOOL_HANDLERS = {
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "list_directory": handle_list_directory,
}

# FastAPI 应用
app = FastAPI(title="Plector MCP Filesystem Server")

# SSE 连接队列
sse_queues = {}


async def handle_request(request):
    """处理 JSON-RPC 2.0 请求"""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return _handle_initialize(req_id)

    elif method == "notifications/initialized":
        return None

    elif method == "tools/list":
        return _handle_tools_list(req_id)

    elif method == "tools/call":
        return await _handle_tools_call(req_id, params)

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"未知方法: {method}"},
        }


def _handle_initialize(req_id):
    """处理 initialize 请求"""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "plector-filesystem-http", "version": "1.0.0"},
        },
    }


def _handle_tools_list(req_id):
    """处理 tools/list 请求"""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"tools": TOOLS},
    }


async def _handle_tools_call(req_id, params):
    """处理 tools/call 请求"""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
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
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": f"错误: {e}"}]},
        }


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE 端点：Server 向 Client 推送事件"""
    queue: asyncio.Queue[dict] = asyncio.Queue()
    session_id = str(id(queue))
    sse_queues[session_id] = queue

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"data": json.dumps(data)}
                except asyncio.TimeoutError:
                    yield {"data": json.dumps({"type": "ping"})}
        finally:
            sse_queues.pop(session_id, None)

    return EventSourceResponse(event_generator())


@app.post("/message")
async def message_endpoint(request: Request):
    """消息端点：Client 发送 JSON-RPC 请求"""
    body = await request.json()
    session_id = request.query_params.get("sessionId", "")

    response = await handle_request(body)

    if response is not None:
        # 通过 SSE 推送响应
        if session_id and session_id in sse_queues:
            await sse_queues[session_id].put(response)
        # 也通过 HTTP 返回（兼容性）
        return response

    return {"status": "ok"}


def main():
    port = 3000
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    print(f"MCP Filesystem Server (HTTP+SSE) 启动: http://127.0.0.1:{port}")
    print(f"SSE: http://127.0.0.1:{port}/sse")
    print(f"Message: http://127.0.0.1:{port}/message")

    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
