import pytest
import asyncio
from core.function_calling import ToolRegistry


@pytest.mark.asyncio
async def test_register_and_get_schemas():
    t = ToolRegistry()
    t.register("echo", "Echo", {"msg": {"type": "string", "description": "消息"}}, lambda msg: msg)
    schemas = t.get_tool_schemas()
    assert len(schemas) == 1
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["strict"] == True
    assert schemas[0]["function"]["parameters"]["additionalProperties"] == False


@pytest.mark.asyncio
async def test_execute_not_found():
    t = ToolRegistry()
    result = await t.execute({"function": {"name": "nonexistent", "arguments": "{}"}})
    assert result.get("jsonrpc") == "2.0"
    assert result.get("error", {}).get("code") == -32601


@pytest.mark.asyncio
async def test_execute_json_parse_error():
    t = ToolRegistry()
    result = await t.execute({"function": {"name": "test", "arguments": "invalid json"}})
    assert result.get("jsonrpc") == "2.0"
    assert result.get("error", {}).get("code") == -32700
