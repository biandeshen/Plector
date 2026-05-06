"""Tests for core.function_calling — ToolRegistry."""

import asyncio

import pytest

from core.function_calling import ToolRegistry

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def registry():
    return ToolRegistry()


# =========================================================================
# ToolRegistry.__init__
# =========================================================================


class TestToolRegistryInit:
    def test_initial_tools_empty(self, registry):
        assert registry._tools == {}

    def test_get_tool_schemas_returns_empty_list(self, registry):
        assert registry.get_tool_schemas() == []


# =========================================================================
# ToolRegistry.register
# =========================================================================


class TestToolRegistryRegister:
    def test_register_adds_tool(self, registry):
        def my_handler(**kwargs):
            return {"data": "ok"}

        registry.register(
            name="health.check",
            description="Check health status",
            input_schema={
                "type": "object",
                "properties": {"timeout": {"type": "integer"}},
                "required": [],
                "additionalProperties": False,
            },
            handler=my_handler,
        )

        assert "health.check" in registry._tools
        tool = registry._tools["health.check"]
        assert tool["handler"] is my_handler
        assert tool["schema"]["function"]["name"] == "health.check"
        assert tool["schema"]["function"]["strict"] is True

    def test_register_wraps_input_schema_when_type_missing(self, registry):
        """If input_schema has no 'type' key, wrap as JSON Schema object."""
        registry.register(
            name="simple",
            description="simple tool",
            input_schema={"name": {"type": "string"}, "count": {"type": "integer"}},
            handler=lambda **kw: {},
        )

        tool = registry._tools["simple"]
        params = tool["schema"]["function"]["parameters"]
        assert params["type"] == "object"
        assert "name" in params["properties"]
        assert "count" in params["properties"]
        assert "required" in params
        assert "name" in params["required"]
        assert "count" in params["required"]

    def test_register_adds_additional_properties_when_missing(self, registry):
        """additionalProperties should default to False."""
        registry.register(
            name="strict_tool",
            description="strict",
            input_schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": [],
            },
            handler=lambda **kw: {},
        )

        params = registry._tools["strict_tool"]["schema"]["function"]["parameters"]
        assert params["additionalProperties"] is False

    def test_register_preserves_existing_additional_properties(self, registry):
        """If additionalProperties is already set, don't override."""
        registry.register(
            name="lenient",
            description="lenient",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
            handler=lambda **kw: {},
        )

        params = registry._tools["lenient"]["schema"]["function"]["parameters"]
        assert params["additionalProperties"] is True

    def test_register_multiple_tools(self, registry):
        def handler_a(**kw):
            return {"result": "a"}

        def handler_b(**kw):
            return {"result": "b"}

        registry.register("tool_a", "desc a", {"type": "object", "properties": {}}, handler_a)
        registry.register("tool_b", "desc b", {"type": "object", "properties": {}}, handler_b)

        assert len(registry._tools) == 2
        assert registry._tools["tool_a"]["handler"] is handler_a
        assert registry._tools["tool_b"]["handler"] is handler_b


# =========================================================================
# ToolRegistry.get_tool_schemas
# =========================================================================


class TestToolRegistryGetToolSchemas:
    def test_returns_schema_list(self, registry):
        registry.register("t1", "desc", {"type": "object", "properties": {}}, lambda **kw: {})
        registry.register("t2", "desc", {"type": "object", "properties": {}}, lambda **kw: {})

        schemas = registry.get_tool_schemas()
        assert len(schemas) == 2
        assert schemas[0]["function"]["name"] == "t1"
        assert schemas[1]["function"]["name"] == "t2"

    def test_schema_has_correct_structure(self, registry):
        registry.register(
            "greet",
            "Say hello",
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            lambda **kw: {},
        )

        schema = registry.get_tool_schemas()[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "greet"
        assert schema["function"]["description"] == "Say hello"
        assert schema["function"]["strict"] is True
        assert schema["function"]["parameters"]["type"] == "object"
        assert "name" in schema["function"]["parameters"]["properties"]


# =========================================================================
# ToolRegistry.execute
# =========================================================================


class TestToolRegistryExecute:
    @pytest.mark.asyncio
    async def test_execute_sync_handler(self, registry):
        def handler(**kwargs):
            return {"data": f"hello {kwargs['name']}"}

        registry.register(
            "greet",
            "desc",
            {"type": "object", "properties": {"name": {"type": "string"}}},
            handler,
        )

        result = await registry.execute({"function": {"name": "greet", "arguments": '{"name": "world"}'}})

        assert result["result"]["data"] == "hello world"

    @pytest.mark.asyncio
    async def test_execute_async_handler(self, registry):
        async def handler(**kwargs):
            await asyncio.sleep(0.01)
            return {"data": f"async {kwargs['x']}"}

        registry.register(
            "async_tool",
            "desc",
            {"type": "object", "properties": {"x": {"type": "int"}}},
            handler,
        )

        result = await registry.execute({"function": {"name": "async_tool", "arguments": '{"x": 42}'}})

        assert result["result"]["data"] == "async 42"

    @pytest.mark.asyncio
    async def test_execute_with_args_as_dict(self, registry):
        """arguments can be a dict (already parsed)."""
        # Handler returns {"result": "direct_dict"}; the execute code unwraps
        # it to "direct_dict" (string), then wraps it as {"data": "direct_dict"}.

        def handler(**kwargs):
            return {"result": kwargs["value"]}

        registry.register(
            "echo",
            "desc",
            {"type": "object", "properties": {"value": {"type": "string"}}},
            handler,
        )

        result = await registry.execute(
            {
                "function": {
                    "name": "echo",
                    "arguments": {"value": "direct_dict"},
                }
            }
        )

        assert result["result"]["data"] == "direct_dict"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, registry):
        result = await registry.execute({"function": {"name": "nonexistent", "arguments": "{}"}})

        assert result["error"]["code"] == -32601
        assert "不存在" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_execute_json_parse_error(self, registry):
        result = await registry.execute({"function": {"name": "any", "arguments": "{invalid json}"}})

        assert result["error"]["code"] == -32700
        assert "JSON 解析失败" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_execute_handler_exception_returns_error(self, registry):
        def failing_handler(**kwargs):
            raise RuntimeError("something broke")

        registry.register(
            "failing",
            "desc",
            {"type": "object", "properties": {}},
            failing_handler,
        )

        result = await registry.execute({"function": {"name": "failing", "arguments": "{}"}})

        assert result["error"]["code"] == -32603
        assert "something broke" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_execute_unwraps_inner_result_key(self, registry):
        """If handler returns {'result': X}, the code unwraps X then wraps as {'data': X}."""
        # Handler returns {"result": "inner_value"}, code unwraps to "inner_value",
        # then wraps as {"data": "inner_value"} since "inner_value" is not a dict.

        def handler(**kwargs):
            return {"result": "inner_value", "extra": "ignored"}

        registry.register(
            "wrap",
            "desc",
            {"type": "object", "properties": {}},
            handler,
        )

        result = await registry.execute({"function": {"name": "wrap", "arguments": "{}"}})

        assert result["result"]["data"] == "inner_value"

    @pytest.mark.asyncio
    async def test_execute_non_dict_return_wraps_in_data(self, registry):
        """Non-dict return gets wrapped in {'data': ...}."""

        def handler(**kwargs):
            return 42

        registry.register(
            "answer",
            "desc",
            {"type": "object", "properties": {}},
            handler,
        )

        result = await registry.execute({"function": {"name": "answer", "arguments": "{}"}})

        assert result["result"]["data"] == 42

    @pytest.mark.asyncio
    async def test_execute_without_result_key_returns_full_dict(self, registry):
        """Dict without 'result' key is used directly."""

        def handler(**kwargs):
            return {"success": True, "value": 100}

        registry.register(
            "custom",
            "desc",
            {"type": "object", "properties": {}},
            handler,
        )

        result = await registry.execute({"function": {"name": "custom", "arguments": "{}"}})

        assert result["result"]["success"] is True
        assert result["result"]["value"] == 100

    @pytest.mark.asyncio
    async def test_json_rpc_format_consistency(self, registry):
        """Response should always have jsonrpc: '2.0'."""

        def handler(**kwargs):
            return {"data": "ok"}

        registry.register(
            "t",
            "desc",
            {"type": "object", "properties": {}},
            handler,
        )

        result = await registry.execute({"function": {"name": "t", "arguments": "{}"}})

        assert "jsonrpc" in result
        assert result["jsonrpc"] == "2.0"


# =========================================================================
# ToolRegistry — deepcopy isolation
# =========================================================================


class TestToolRegistryDeepCopy:
    def test_get_tool_schemas_returns_independent_copy(self, registry):
        """Modifying returned schemas should not affect internal state."""
        registry.register("t1", "desc", {"type": "object", "properties": {}}, lambda **kw: {})

        schemas = registry.get_tool_schemas()
        assert len(schemas) == 1

        # Mutate the returned list
        schemas.clear()

        # Internal state should be unchanged
        assert len(registry._tools) == 1
        schemas2 = registry.get_tool_schemas()
        assert len(schemas2) == 1
        assert schemas2[0]["function"]["name"] == "t1"

    def test_get_tool_schemas_nested_mutation_isolated(self, registry):
        """Deep mutation of schema dict should not leak."""
        registry.register(
            "inner",
            "desc",
            {"type": "object", "properties": {"x": {"type": "string"}}},
            lambda **kw: {},
        )

        schemas = registry.get_tool_schemas()
        # Mutate nested field
        schemas[0]["function"]["parameters"]["properties"] = {}
        schemas[0]["function"]["name"] = "hijacked"

        # Original should be intact
        original = registry._tools["inner"]
        assert original["schema"]["function"]["name"] == "inner"
        assert "x" in original["schema"]["function"]["parameters"]["properties"]


# =========================================================================
# ToolRegistry — TypeError coverage
# =========================================================================


class TestToolRegistryTypeError:
    @pytest.mark.asyncio
    async def test_handler_missing_required_arg_returns_error(self, registry):
        """When handler raises TypeError due to missing arg, it returns JSON-RPC error."""

        def strict_handler(*, required_arg, **kwargs):
            return {"data": required_arg}

        registry.register(
            "strict",
            "desc",
            {"type": "object", "properties": {"required_arg": {"type": "string"}}},
            strict_handler,
        )

        result = await registry.execute({"function": {"name": "strict", "arguments": "{}"}})

        assert result["error"]["code"] == -32603

    @pytest.mark.asyncio
    async def test_handler_unexpected_kwargs_returns_error(self, registry):
        """When handler rejects unexpected kwargs, it should return error."""

        def no_kwargs_handler():
            return {"data": "ok"}

        registry.register(
            "no_args",
            "desc",
            {"type": "object", "properties": {}},
            no_kwargs_handler,
        )

        result = await registry.execute({"function": {"name": "no_args", "arguments": '{"extra": "value"}'}})

        assert result["error"]["code"] == -32603
