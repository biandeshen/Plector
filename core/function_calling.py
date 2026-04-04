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
        执行工具调用

        参数:
            tool_call: LLM 返回的 tool_call 对象
                OpenAI 格式: {"function": {"name": "...", "arguments": "..."}, "id": "..."}
                Ollama 格式: {"function": {"name": "...", "arguments": {...}}}

        返回:
            {"success": bool, "data": any, "error": str or None}
        """
        name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]
        # 兼容两种格式：OpenAI 返回字符串，Ollama 返回 dict
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "data": None, "error": f"工具 {name} 不存在"}

        try:
            result = tool["handler"](**arguments)
            if asyncio.iscoroutine(result):
                result = await result
            return result if isinstance(result, dict) else {"success": True, "data": result, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
