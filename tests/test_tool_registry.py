import pytest
import asyncio
from core.function_calling import ToolRegistry


@pytest.mark.asyncio
async def test_register_and_execute():
    t = ToolRegistry()
    t.register("echo", "Echo", {"msg": {"type": "string"}}, lambda msg: msg)
    schemas = t.get_tool_schemas()
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "echo"
