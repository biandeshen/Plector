import asyncio
import importlib.util
import logging
import types

from .skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


def _load_module_sync(skill_name: str, module_path) -> types.ModuleType:
    """Synchronously load a skill module (runs in thread pool)."""
    spec = importlib.util.spec_from_file_location(skill_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillHandler:
    def __init__(self, registry: SkillRegistry, mcp_client=None):
        self.registry = registry
        self.mcp_client = mcp_client

    async def execute(self, skill_name: str, method: str, params: dict) -> dict:
        skill = self.registry.get_skill(skill_name)
        if not skill:
            return {"error": f"技能 {skill_name} 不存在"}
        if skill["module"] is None:
            module_path = skill["path"] / "implementation.py"
            loop = asyncio.get_running_loop()
            skill["module"] = await loop.run_in_executor(None, _load_module_sync, skill_name, module_path)
        handler_class = getattr(skill["module"], "SkillHandler", None)
        if not handler_class:
            return {"error": f"技能 {skill_name} 没有 SkillHandler 类"}
        instance = handler_class()
        func = getattr(instance, method, None)
        if not func:
            return {"error": f"方法 {method} 不存在"}
        result = func(**params)
        if asyncio.iscoroutine(result):
            result = await result

        # 拦截 _mcp_call，自动路由到 MCP Server
        if isinstance(result, dict) and "_mcp_call" in result:
            return await self._handle_mcp_call(result)

        return {"result": result}

    async def _handle_mcp_call(self, mcp_request: dict) -> dict:
        """处理技能的 MCP 代理请求

        mcp_request 格式:
            {"_mcp_call": "server_name", "tool": "tool_name", "args": {...}}

        复用 AgentLoop 已初始化的 MCPClient 连接，
        避免重复建连和端口冲突。
        """
        server_name = mcp_request["_mcp_call"]
        tool_name = mcp_request["tool"]
        args = mcp_request.get("args", {})

        if not self.mcp_client:
            return {"error": "MCP Client 未初始化，无法代理 _mcp_call"}

        server = self.mcp_client.servers.get(server_name)
        if not server:
            return {"error": f"MCP Server '{server_name}' 未连接"}

        try:
            raw_result = await server.call_tool(tool_name, args)
            # 将 MCP JSON-RPC 结果转为 Plector 统一格式
            if "error" in raw_result:
                err = raw_result["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return {"error": f"MCP 调用失败: {msg}"}
            mcp_result = raw_result.get("result", {})
            content = mcp_result.get("content", [])
            text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return {
                "result": {
                    "success": True,
                    "data": {"text": "\n".join(text_parts), "raw": mcp_result},
                    "error": None,
                }
            }
        except Exception as e:
            logger.error(f"MCP 调用失败: {server_name}.{tool_name} - {e}", exc_info=True)
            return {"error": f"MCP 调用失败: {e!s}"}
