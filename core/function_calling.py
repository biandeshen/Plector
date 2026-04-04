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
        arguments = tool_call["function"]["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        # 先精确匹配
        tool = self._tools.get(name)

        # OpenAI 可能把 . 替换为 _，遍历所有工具找最匹配的
        if not tool:
            for registered_name in self._tools.keys():
                # health_monitor.check_health vs health_monitor_check_health
                # 把注册的 . 替换为 _，看是否匹配
                if registered_name.replace(".", "_") == name:
                    tool = self._tools[registered_name]
                    break

        if not tool:
            available = list(self._tools.keys())
            return {
                "error": f"工具 {name} 不存在（可用工具: {', '.join(available)}）"
            }

        result = tool["handler"](**arguments)
        if asyncio.iscoroutine(result):
            result = await result

        # 如果返回值是 {"result": xxx}，提取 result
        if isinstance(result, dict) and "result" in result:
            result = result["result"]
        elif isinstance(result, dict) and "error" in result:
            # 错误情况，保持原样
            pass

        return result
