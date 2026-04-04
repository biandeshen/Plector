#!/usr/bin/env python3
"""
MCP Client - 连接外部 MCP Server，发现并调用工具

功能：
    1. 通过 stdio 或 HTTP+SSE 连接 MCP Server
    2. 发现远程工具（tools/list）
    3. 调用远程工具（tools/call）
    4. 将远程工具注册到 ToolRegistry

通信协议：JSON-RPC 2.0

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import asyncio
import json
import logging
import os
from collections.abc import Callable

logger = logging.getLogger(__name__)


class MCPServer:
    """单个 MCP Server 连接"""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.transport = config.get("transport", "stdio")
        self.description = config.get("description", "")
        self.process = None
        self._request_id = 0
        self._connected = False

    async def connect(self):
        """连接 MCP Server"""
        if self.transport == "stdio":
            await self._connect_stdio()
        elif self.transport == "http":
            await self._connect_http()
        else:
            raise ValueError(f"不支持的 transport: {self.transport}")

    async def _connect_stdio(self):
        """通过 stdio 连接"""
        command = self.config.get("command")
        args = self.config.get("args", [])
        env_config = self.config.get("env", {})

        # 解析环境变量
        env = {**os.environ}
        for key, value in env_config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                env[key] = os.environ.get(env_name, "")
            else:
                env[key] = str(value)

        try:
            self.process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            self._connected = True
            logger.info(f"MCP Server '{self.name}' 已连接（stdio）")

            # 发送 initialize 请求
            await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}},
                    "clientInfo": {"name": "Plector", "version": "1.0.0"},
                },
            )
        except FileNotFoundError:
            logger.error(f"MCP Server '{self.name}' 启动失败：命令 '{command}' 不存在")
            self._connected = False
        except Exception as e:
            logger.error(f"MCP Server '{self.name}' 连接失败: {e}")
            self._connected = False

    async def _connect_http(self):
        """通过 HTTP+SSE 连接"""
        # TODO: 实现 HTTP+SSE 传输
        logger.warning(f"MCP Server '{self.name}' HTTP 传输尚未实现")
        self._connected = False

    async def list_tools(self) -> list[dict]:
        """发现远程工具"""
        if not self._connected:
            return []
        try:
            response = await self._send_request("tools/list", {})
            return response.get("result", {}).get("tools", [])
        except Exception as e:
            logger.error(f"获取 MCP Server '{self.name}' 工具列表失败: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用远程工具"""
        if not self._connected:
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": f"MCP Server '{self.name}' 未连接"}}
        try:
            response = await self._send_request(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": arguments,
                },
            )
            return response
        except Exception as e:
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}

    async def _send_request(self, method: str, params: dict) -> dict:
        """发送 JSON-RPC 2.0 请求"""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        request_line = json.dumps(request) + "\n"

        self.process.stdin.write(request_line.encode("utf-8"))
        await self.process.stdin.drain()

        # 读取响应
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise ConnectionError(f"MCP Server '{self.name}' 无响应")

        response = json.loads(response_line.decode("utf-8"))

        # 跳过通知（无 id 的消息）
        while "id" not in response:
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise ConnectionError(f"MCP Server '{self.name}' 无响应")
            response = json.loads(response_line.decode("utf-8"))

        return response

    async def disconnect(self):
        """断开连接"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self._connected = False
            logger.info(f"MCP Server '{self.name}' 已断开")


class MCPClient:
    """MCP Client，管理多个 MCP Server 连接"""

    def __init__(self, config: dict):
        self.servers: dict[str, MCPServer] = {}
        self.server_config = config.get("mcp", {}).get("servers", {})

    async def connect_all(self):
        """连接所有 enabled 的 MCP Server"""
        for name, server_config in self.server_config.items():
            if not server_config.get("enabled", False):
                logger.info(f"MCP Server '{name}' 未启用，跳过")
                continue

            server = MCPServer(name, server_config)
            await server.connect()
            if server._connected:
                self.servers[name] = server

    async def list_all_tools(self) -> dict[str, list[dict]]:
        """获取所有 MCP Server 的工具列表"""
        all_tools = {}
        for name, server in self.servers.items():
            tools = await server.list_tools()
            all_tools[name] = tools
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        """调用指定 MCP Server 的工具"""
        server = self.servers.get(server_name)
        if not server:
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"MCP Server '{server_name}' 未连接"}}
        return await server.call_tool(tool_name, arguments)

    def register_to_tool_registry(self, tool_registry, all_tools: dict[str, list[dict]]):
        """将远程工具注册到 ToolRegistry"""
        for server_name, tools in all_tools.items():
            for tool in tools:
                remote_name = f"mcp_{server_name}_{tool['name']}"
                tool_registry.register(
                    name=remote_name,
                    description=f"[MCP:{server_name}] {tool.get('description', '')}",
                    input_schema=tool.get(
                        "inputSchema",
                        {
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        },
                    ),
                    handler=self._create_handler(server_name, tool["name"]),
                )
                logger.info(f"注册远程工具: {remote_name}")

    def _create_handler(self, server_name: str, tool_name: str) -> Callable:
        """创建远程工具的处理函数"""

        async def handler(**kwargs):
            result = await self.call_tool(server_name, tool_name, kwargs)
            # 将 MCP 结果转换为 Plector 格式
            if "error" in result:
                return {"success": False, "data": None, "error": result["error"].get("message", "未知错误")}
            mcp_result = result.get("result", {})
            content = mcp_result.get("content", [])
            # 提取文本内容
            text_parts = []
            for item in content:
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return {
                "success": True,
                "data": {"text": "\n".join(text_parts), "raw": mcp_result},
                "error": None,
            }

        return handler

    async def disconnect_all(self):
        """断开所有 MCP Server 连接"""
        for name, server in self.servers.items():
            await server.disconnect()
        self.servers.clear()
