import json
import asyncio
from typing import Callable, Dict


class ToolRegistry:
    """工具注册表，输出 OpenAI Function Calling 格式"""

    def __init__(self):
        self._tools: Dict[str, Dict] = {}

    def register(self, name: str, description: str, input_schema: dict, handler: Callable):
        """
        注册工具

        参数:
            name: 工具名称（如 health_monitor.check_health）
            description: 工具描述
            input_schema: JSON Schema 格式的参数定义
            handler: 异步或同步的处理函数
        """
        # 确保 input_schema 是完整 JSON Schema
        if "type" not in input_schema:
            input_schema = {
                "type": "object",
                "properties": input_schema,
                "required": list(input_schema.keys()),
                "additionalProperties": False,
            }
        # 确保 additionalProperties 存在
        if "additionalProperties" not in input_schema:
            input_schema["additionalProperties"] = False

        self._tools[name] = {
            "handler": handler,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": input_schema,
                    "strict": True,
                }
            }
        }

    def get_tool_schemas(self) -> list:
        """获取所有工具的 OpenAI Function Calling Schema"""
        return [info["schema"] for info in self._tools.values()]

    async def execute(self, tool_call: dict) -> dict:
        """
        执行工具调用，返回 JSON-RPC 2.0 格式
        """
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
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"工具 {name} 不存在"}
            }

        try:
            result = tool["handler"](**arguments)
            if asyncio.iscoroutine(result):
                result = await result

            # 解包 result
            if isinstance(result, dict) and "result" in result:
                result = result["result"]

            return {
                "jsonrpc": "2.0",
                "result": result if isinstance(result, dict) else {"data": result}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)}
            }
