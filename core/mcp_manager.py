#!/usr/bin/env python3
"""
MCP Manager - 管理多个 MCP Server 连接

功能：
    1. 加载 MCP Server 配置
    2. 连接所有启用的 MCP Server
    3. 获取工具列表
    4. 调用工具

Author: Plector
Version: 1.0.0
Created: 2026-04-06
"""

import logging

import yaml

from core.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class MCPManager:
    """MCP Server 管理器"""

    def __init__(self):
        self.clients: dict[str, MCPClient] = {}
        self.tool_registry: dict[str, dict] = {}  # {server_name_tool_name: tool_info}

    async def load_config(self, config_path: str = "config/config.yaml"):
        """加载 MCP Server 配置"""
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        mcp_config = config.get("mcp", {}).get("servers", {})

        for name, server_config in mcp_config.items():
            if not server_config.get("enabled", False):
                logger.info(f"MCP Server '{name}' 未启用，跳过")
                continue

            client = MCPClient({"mcp": {"servers": {name: server_config}}})
            await client.connect_all()

            if name in client.servers:
                self.clients[name] = client

                # 注册工具
                tools = await client.list_all_tools()
                server_tools = tools.get(name, [])
                for tool in server_tools:
                    tool_key = f"{name}_{tool['name']}"
                    self.tool_registry[tool_key] = {
                        "server": name,
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "inputSchema": tool.get("inputSchema", {}),
                    }

                logger.info(f"MCP Server '{name}' 已连接，工具数: {len(server_tools)}")

    async def list_tools(self, server_name: str | None = None) -> dict[str, list]:
        """获取工具列表"""
        if server_name:
            client = self.clients.get(server_name)
            if not client:
                return {}
            return await client.list_all_tools()

        # 返回所有服务器的工具
        all_tools = {}
        for name, client in self.clients.items():
            tools = await client.list_all_tools()
            all_tools.update(tools)
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> dict:
        """调用工具"""
        client = self.clients.get(server_name)
        if not client:
            return {"error": f"MCP Server '{server_name}' 未连接"}
        return await client.call_tool(server_name, tool_name, arguments)

    def get_all_tools(self) -> list[dict]:
        """获取所有 MCP 工具（用于注册到技能系统）"""
        tools = []
        for tool_key, tool_info in self.tool_registry.items():
            tools.append(
                {
                    "name": tool_info["name"],
                    "description": tool_info.get("description", ""),
                    "inputSchema": tool_info.get("inputSchema", {}),
                    "server": tool_info["server"],
                }
            )
        return tools

    async def disconnect_all(self):
        """断开所有 MCP Server 连接"""
        for client in self.clients.values():
            await client.disconnect_all()
        self.clients.clear()
        self.tool_registry.clear()
