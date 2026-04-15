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


@pytest.mark.asyncio
async def test_execute_success():
    t = ToolRegistry()
    t.register("add", "Add", {"a": {"type": "integer"}, "b": {"type": "integer"}}, lambda a, b: {"sum": a + b})
    result = await t.execute({"function": {"name": "add", "arguments": '{"a":1,"b":2}'}})
    assert result.get("result", {}).get("sum") == 3


@pytest.mark.asyncio
async def test_execute_result_unpacking():
    """结果包含 result 键时应正确解包"""
    t = ToolRegistry()
    t.register("wrapped", "Wrapped", {}, lambda: {"result": "data"})
    result = await t.execute({"function": {"name": "wrapped", "arguments": "{}"}})
    assert result.get("result") == "data"


@pytest.mark.asyncio
async def test_register_does_not_mutate_schema():
    """register 不应修改传入的 input_schema"""
    original = {"type": "object", "properties": {"x": {"type": "string"}}}
    original_copy = {"type": "object", "properties": {"x": {"type": "string"}}}
    t = ToolRegistry()
    t.register("nomutate", "NoMutate", original, lambda: None)
    assert original == original_copy
