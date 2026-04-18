# MCP Server 开发指南

本文档介绍如何在 Plector 中创建和注册 MCP Server。

## 目录

1. [概述](#概述)
2. [创建 MCP Server](#创建-mcp-server)
3. [实现 JSON-RPC 协议](#实现-json-rpc-协议)
4. [注册 Server](#注册-server)
5. [测试 Server](#测试-server)
6. [完整示例](#完整示例)

---

## 概述

Plector 使用 MCP (Model Context Protocol) 与外部服务器通信。MCP Server 通过 JSON-RPC 2.0 协议提供工具（tools），Plector 的 MCP Client 负责连接和调用。

### 支持的传输方式

| 传输方式 | 说明 | 配置字段 |
|----------|------|----------|
| `stdio` | 标准输入/输出（推荐） | `command`, `args` |
| `http` | HTTP + SSE | `url` |

---

## 创建 MCP Server

### 1. 创建服务器文件

在 `servers/` 目录下创建新的 Python 文件：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{MCP Server 名称}
功能：
    1. {功能描述}
    ...

协议：
    JSON-RPC 2.0 over stdio

Author: Plector
Version: 1.0.0
"""

import json
import sys
from pathlib import Path

# 从命令行参数获取根目录或配置
if len(sys.argv) > 1:
    CONFIG = sys.argv[1]
```

### 2. 定义工具

每个工具需要包含 `name`、`description` 和 `inputSchema`：

```python
TOOLS = [
    {
        "name": "tool_name",           # 工具名称（蛇形命名）
        "description": "工具描述",      # 供 LLM 理解用途
        "inputSchema": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数描述"},
                "param2": {"type": "integer", "description": "参数描述"},
            },
            "required": ["param1"],     # 必填参数
            "additionalProperties": False,
        },
    },
]
```

---

## 实现 JSON-RPC 协议

MCP 协议基于 JSON-RPC 2.0，主要方法：

| 方法 | 说明 |
|------|------|
| `initialize` | 初始化连接，返回服务器能力 |
| `notifications/initialized` | 客户端就绪通知（无需响应） |
| `tools/list` | 列出所有可用工具 |
| `tools/call` | 调用指定工具 |

### 响应格式

```python
def _initialize(req_id) -> dict:
    """处理 initialize 请求"""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "server-name", "version": "1.0.0"},
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
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": f"错误: {type(e).__name__}: {e}"}]},
        }
```

### 请求分发

```python
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
```

### 主循环

```python
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
```

---

## 注册 Server

在 `config/config.yaml` 的 `mcp.servers` 下添加配置：

```yaml
mcp:
  servers:
    my_server:
      enabled: true
      transport: "stdio"              # 或 "http"
      command: "python"               # 可执行命令
      args: ["servers/my_server.py"]  # 命令参数
      description: "我的 MCP Server"  # 描述
      # env:                          # 环境变量（可选）
      #   API_KEY: "${API_KEY}"
```

### HTTP+SSE 配置

```yaml
mcp:
  servers:
    my_http_server:
      enabled: true
      transport: "http"
      url: "http://localhost:3000/sse"
      description: "HTTP MCP Server"
```

---

## 测试 Server

### 1. 手动测试

直接运行服务器并发送 JSON-RPC 请求：

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | python servers/my_server.py
```

### 2. 自动化测试

```python
import asyncio
import json
import subprocess

async def test_mcp_server():
    proc = await asyncio.create_subprocess_exec(
        "python", "servers/my_server.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # 发送 initialize
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0.0"}
        }
    }
    proc.stdin.write(json.dumps(request).encode() + b"\n")
    await proc.stdin.drain()

    # 读取响应
    response = await proc.stdout.readline()
    print(json.loads(response.decode()))

    await proc.terminate()

asyncio.run(test_mcp_server())
```

### 3. 通过 Plector 测试

启动 Plector 后，MCP Server 会自动连接。可在日志中查看：

```
INFO - MCP Server 'my_server' 已连接（stdio）
INFO - 注册远程工具: mcp_my_server_tool_name
```

---

## 完整示例

参考 `servers/filesystem_server.py`，这是一个功能完整的 MCP Server 实现：

### 核心组件

1. **工具定义** (`TOOLS`)：声明所有可用工具及其参数模式
2. **工具处理器** (`TOOL_HANDLERS`)：将工具名称映射到处理函数
3. **请求处理** (`handle_request`)：根据方法名分发请求
4. **主循环** (`main`)：读写 stdio 的无限循环

### 安全考虑

```python
FORBIDDEN_PATHS = ["/", "C:\\", "/etc", "/usr"]

def check_safe_path(filepath: str) -> Path:
    """检查路径是否在允许范围内"""
    path = (ROOT_DIR / filepath).resolve()
    try:
        path.relative_to(ROOT_DIR)
    except ValueError:
        raise PermissionError(f"路径超出根目录范围: {filepath}")
    return path
```

### 错误处理

所有错误应返回在 `result.content[0].text` 中，而不是 `error` 字段：

```python
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
```

---

## 相关文档

- [配置文件参考](./Configuration_Reference.md)
- [MCP Client 实现](../core/mcp_client.py)
- [技能开发指南](../standards/Skill_Development_Plector.md)
