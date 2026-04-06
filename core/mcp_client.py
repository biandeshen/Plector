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

import httpx

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
                env_value = os.environ.get(env_name)
                if env_value is None:
                    raise ValueError(f"环境变量 {env_name} 未设置")
                env[key] = env_value
            else:
                env[key] = str(value)

        # 扩展 PATH（Windows 优先）
        uv_path = r"C:\Users\dev\.local\bin"
        if "PATH" in env and uv_path not in env["PATH"]:
            env["PATH"] = f"{uv_path};{env['PATH']}"

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
        url = self.config.get("url", "")
        if not url:
            logger.error(f"MCP Server '{self.name}' 未配置 url")
            self._connected = False
            return

        self._sse_url = url
        self._message_url = url.replace("/sse", "/message")
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._sse_task = None
        self._response_queue = asyncio.Queue()

        try:
            # 启动 SSE 监听
            self._sse_task = asyncio.create_task(self._listen_sse())

            # 发送 initialize 请求
            await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}},
                    "clientInfo": {"name": "Plector", "version": "1.0.0"},
                },
            )

            self._connected = True
            logger.info(f"MCP Server '{self.name}' 已连接（HTTP+SSE）: {url}")
        except Exception as e:
            logger.error(f"MCP Server '{self.name}' HTTP+SSE 连接失败: {e}")
            self._connected = False

    async def _listen_sse(self):
        """监听 SSE 事件"""
        try:
            async with self._http_client.stream("GET", self._sse_url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            if "id" in event:
                                await self._response_queue.put(event)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"MCP Server '{self.name}' SSE 监听中断: {e}")

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

        if self.transport == "stdio":
            return await self._send_request_stdio(request)
        elif self.transport == "http":
            return await self._send_request_http(request)
        else:
            raise ValueError(f"不支持的 transport: {self.transport}")

    async def _send_request_stdio(self, request: dict) -> dict:
        """通过 stdio 发送请求"""
        request_line = json.dumps(request) + "\n"

        self.process.stdin.write(request_line.encode("utf-8"))
        await self.process.stdin.drain()

        response_line = await self.process.stdout.readline()
        if not response_line:
            raise ConnectionError(f"MCP Server '{self.name}' 无响应")

        decoded = response_line.decode("utf-8").strip()

        # 跳过非 JSON 行（如日志、错误信息）
        while not decoded.startswith("{"):
            logger.debug(f"跳过非 JSON 行: {decoded[:100]}")
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise ConnectionError(f"MCP Server '{self.name}' 无响应")
            decoded = response_line.decode("utf-8").strip()

        response = json.loads(decoded)

        while "id" not in response:
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise ConnectionError(f"MCP Server '{self.name}' 无响应")
            response = json.loads(response_line.decode("utf-8"))

        return response

    async def _send_request_http(self, request: dict) -> dict:
        """通过 HTTP+SSE 发送请求"""
        response = await self._http_client.post(
            self._message_url,
            json=request,
        )
        response.raise_for_status()

        # 尝试从 HTTP 响应获取
        try:
            http_response = response.json()
            if "id" in http_response:
                return http_response
        except Exception:
            pass

        # 从 SSE 队列获取
        try:
            sse_response = await asyncio.wait_for(self._response_queue.get(), timeout=10.0)
            return sse_response
        except asyncio.TimeoutError as err:
            raise ConnectionError(f"MCP Server '{self.name}' SSE 响应超时") from err

    async def disconnect(self):
        """断开连接"""
        if self.transport == "stdio" and self.process:
            self.process.terminate()
            await self.process.wait()
        elif self.transport == "http":
            if self._sse_task:
                self._sse_task.cancel()
            if hasattr(self, "_http_client"):
                await self._http_client.aclose()
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

    async def close_all(self):
        """断开所有 MCP Server 连接"""
        for name, server in list(self.servers.items()):
            try:
                await server.disconnect()
            except Exception as e:
                logger.warning(f"断开 MCP Server '{name}' 失败: {e}")
        self.servers.clear()
        logger.info("所有 MCP Server 已断开")

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
