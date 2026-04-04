import json
import asyncio
from typing import Callable, Dict, Any

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict] = {}

    def register(self, name: str, description: str, parameters: dict, handler: Callable):
        self._tools[name] = {
            "handler": handler,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }
        }

    def get_tool_schemas(self) -> list:
        return [info["schema"] for info in self._tools.values()]

    async def execute(self, tool_call: dict) -> dict:
        name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"工具 {name} 不存在"}
        result = tool["handler"](**arguments)
        if asyncio.iscoroutine(result):
            result = await result
        return {"result": result}
