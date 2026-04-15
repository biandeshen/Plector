import json
from pathlib import Path


class SkillRegistry:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: dict[str, dict] = {}
        self.mcp_tools: dict[str, dict] = {}  # MCP 工具注册表

    def scan(self):
        if not self.skills_dir.exists():
            return
        for skill_path in self.skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            json_file = skill_path / "skill.json"
            if json_file.exists():
                with open(json_file, encoding="utf-8") as f:
                    meta = json.load(f)
                self.skills[meta["name"]] = {"path": skill_path, "meta": meta, "module": None}

    def get_skill(self, name: str) -> dict | None:
        return self.skills.get(name)

    def register_mcp_tool(self, server: str, name: str, description: str, input_schema: dict):
        """注册 MCP 工具"""
        tool_name = f"mcp_{server}_{name}"
        self.mcp_tools[tool_name] = {
            "name": tool_name,
            "description": description,
            "inputSchema": input_schema,
            "server": server,
            "original_name": name,
        }

    async def load_mcp_tools(self):
        """加载 MCP 工具到技能注册表"""
        import logging

        from core.mcp_client import MCPClient

        logger = logging.getLogger(__name__)

        try:
            client = await MCPClient.from_config()
            all_tools = await client.list_all_tools()

            for server_name, tools in all_tools.items():
                for tool in tools:
                    self.register_mcp_tool(
                        server=server_name,
                        name=tool["name"],
                        description=tool.get("description", ""),
                        input_schema=tool.get("inputSchema", {}),
                    )

            await client.close_all()
            logger.info(f"MCP 工具加载完成: {sum(len(v) for v in all_tools.values())} 个")
        except Exception as e:
            logger.warning(f"MCP 工具加载失败（不影响主流程）: {e}")

    def get_all_tools(self) -> list[dict]:
        """获取所有工具（技能工具 + MCP 工具）"""
        tools = []

        # 技能工具
        for skill_name, skill_data in self.skills.items():
            meta = skill_data["meta"]
            for tool in meta.get("tools", []):
                tools.append(
                    {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "inputSchema": tool.get("inputSchema", {}),
                        "type": "skill",
                        "skill": skill_name,
                    }
                )

        # MCP 工具
        for tool_name, tool_data in self.mcp_tools.items():
            tools.append(
                {
                    "name": tool_name,
                    "description": tool_data.get("description", ""),
                    "inputSchema": tool_data.get("inputSchema", {}),
                    "type": "mcp",
                    "server": tool_data["server"],
                }
            )

        return tools
