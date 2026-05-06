"""Tests for core.mcp_client — MCPServer and MCPClient."""

import asyncio
import json
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from core.mcp_client import MCPClient, MCPServer

# =========================================================================
# MCPServer — __init__
# =========================================================================


class TestMCPServerInit:
    def test_defaults_from_config(self):
        config = {
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-server"],
            "description": "test server",
        }
        server = MCPServer("test", config)
        assert server.name == "test"
        assert server.transport == "stdio"
        assert server.process is None
        assert server._request_id == 0
        assert server._connected is False
        assert server._timeout == 30.0
        assert server._sse_timeout == 10.0

    def test_custom_timeouts(self):
        config = {"transport": "http", "timeout": 60.0, "sse_timeout": 15.0}
        server = MCPServer("slow", config)
        assert server._timeout == 60.0
        assert server._sse_timeout == 15.0


# =========================================================================
# MCPServer — request_id
# =========================================================================


class TestMCPServerRequestId:
    @pytest.mark.asyncio
    async def test_request_id_increments(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        assert server._request_id == 0

        async def fake_send_stdio(req):
            return {"jsonrpc": "2.0", "id": req["id"], "result": {}}

        with patch.object(server, "_send_request_stdio", side_effect=fake_send_stdio):
            r1 = await server._send_request("test.method", {"a": 1})
            r2 = await server._send_request("test.method", {"b": 2})
            r3 = await server._send_request("test.method", {"c": 3})

        assert r1["id"] == 1
        assert r2["id"] == 2
        assert r3["id"] == 3
        assert server._request_id == 3


# =========================================================================
# MCPServer — connect
# =========================================================================


class TestMCPServerConnect:
    @pytest.mark.asyncio
    async def test_unsupported_transport_raises_value_error(self):
        server = MCPServer("bad", {"transport": "unknown"})
        with pytest.raises(ValueError, match="不支持的 transport"):
            await server.connect()

    @pytest.mark.asyncio
    async def test_connect_stdio_creates_subprocess(self):
        server = MCPServer(
            "sqlite",
            {"transport": "stdio", "command": "uvx", "args": ["mcp-server-sqlite"]},
        )

        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()

        init_response = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}})
        mock_process.stdout.readline = AsyncMock(return_value=init_response.encode("utf-8") + b"\n")

        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_process):
            await server.connect()

        assert server._connected is True
        assert server.process is mock_process

    @pytest.mark.asyncio
    async def test_connect_stdio_file_not_found(self, caplog):
        server = MCPServer("missing", {"transport": "stdio", "command": "nonexistent-binary"})

        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            await server.connect()

        assert server._connected is False
        assert "启动失败" in caplog.text


# =========================================================================
# MCPServer — _send_request_stdio
# =========================================================================


class TestMCPServerSendRequestStdio:
    @pytest.mark.asyncio
    async def test_sends_json_rpc_and_parses_response(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        server.process = MagicMock()
        server.process.stdin = AsyncMock()
        server.process.stdout = AsyncMock()

        request_id = 42
        server._request_id = request_id - 1  # will become 42 on next send

        response_payload = {
            "jsonrpc": "2.0",
            "id": 42,
            "result": {"tools": []},
        }
        server.process.stdout.readline = AsyncMock(return_value=json.dumps(response_payload).encode("utf-8") + b"\n")

        # The stdio path doesn't check _connected flag; mock the readline.
        with patch.object(server.process.stdout, "readline", return_value=...):
            # Actually use our mocked readline directly
            pass

        server.process.stdout.readline = AsyncMock(return_value=json.dumps(response_payload).encode("utf-8") + b"\n")

        response = await server._send_request("tools/list", {})

        written = server.process.stdin.write.call_args[0][0]
        sent = json.loads(written)
        assert sent["jsonrpc"] == "2.0"
        assert sent["id"] == 42
        assert sent["method"] == "tools/list"
        assert sent["params"] == {}

        assert response == response_payload

    @pytest.mark.asyncio
    async def test_skips_non_json_lines(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        server.process = MagicMock()
        server.process.stdin = AsyncMock()
        server.process.stdout = AsyncMock()

        server._request_id = 0
        response_payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}

        server.process.stdout.readline = AsyncMock(
            side_effect=[
                b"[log] info message\n",
                b"debug output\n",
                json.dumps(response_payload).encode("utf-8") + b"\n",
            ]
        )

        response = await server._send_request("ping", {})
        assert response == response_payload

    @pytest.mark.asyncio
    async def test_empty_response_raises_connection_error(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        server.process = MagicMock()
        server.process.stdin = AsyncMock()
        server.process.stdout = AsyncMock()

        server.process.stdout.readline = AsyncMock(return_value=b"")

        with pytest.raises(ConnectionError, match="无响应"):
            await server._send_request("ping", {})

    @pytest.mark.asyncio
    async def test_timeout_on_readline(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx", "timeout": 0.01})
        server.process = MagicMock()
        server.process.stdin = AsyncMock()
        server.process.stdout = AsyncMock()

        server.process.stdout.readline = AsyncMock(side_effect=asyncio.TimeoutError("timed out"))

        with pytest.raises(asyncio.TimeoutError):
            await server._send_request("ping", {})


# =========================================================================
# MCPServer — _send_request_http
# =========================================================================


class TestMCPServerSendRequestHttp:
    @pytest.mark.asyncio
    async def test_sends_post_and_returns_direct_response(self):
        server = MCPServer(
            "http-test",
            {"transport": "http", "url": "http://localhost:8000/sse"},
        )
        server._http_client = AsyncMock()
        server._message_url = "http://localhost:8000/message"
        server._pending_requests = {}

        direct_response = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json = MagicMock(return_value=direct_response)

        server._http_client.post = AsyncMock(return_value=mock_post_response)

        response = await server._send_request("tools/list", {})
        assert response == direct_response

        server._http_client.post.assert_called_once_with("http://localhost:8000/message", json=ANY)

    @pytest.mark.asyncio
    async def test_http_with_sse_fallback(self):
        server = MCPServer(
            "http-test",
            {"transport": "http", "url": "http://localhost:8000/sse"},
        )
        server._http_client = AsyncMock()
        server._message_url = "http://localhost:8000/message"
        server._pending_requests = {}
        server._sse_timeout = 5.0
        server._connected = True

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json = MagicMock(side_effect=json.JSONDecodeError("no", "", 0))
        server._http_client.post = AsyncMock(return_value=mock_post_response)

        async def run_and_collect():
            return await server._send_request("tools/list", {})

        task = asyncio.create_task(run_and_collect())
        # Yield control so _send_request_http creates the future and waits
        await asyncio.sleep(0.05)

        # Now _pending_requests should contain the future
        assert len(server._pending_requests) == 1
        req_id = next(iter(server._pending_requests))
        future = server._pending_requests[req_id]
        future.set_result({"jsonrpc": "2.0", "id": req_id, "result": {"sse": True}})

        response = await task
        assert response["result"]["sse"] is True

    @pytest.mark.asyncio
    async def test_http_sse_timeout(self):
        server = MCPServer(
            "http-test",
            {"transport": "http", "url": "http://localhost:8000/sse"},
        )
        server._http_client = AsyncMock()
        server._message_url = "http://localhost:8000/message"
        server._pending_requests = {}
        server._sse_timeout = 0.01
        server._connected = True

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json = MagicMock(side_effect=json.JSONDecodeError("no", "", 0))

        server._http_client.post = AsyncMock(return_value=mock_post_response)

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        with (
            patch.object(loop, "create_future", return_value=future),
            pytest.raises(ConnectionError, match="SSE 响应超时"),
        ):
            await server._send_request("tools/list", {})


# =========================================================================
# MCPServer — list_tools / call_tool
# =========================================================================


class TestMCPServerToolMethods:
    @pytest.mark.asyncio
    async def test_list_tools_when_not_connected(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        tools = await server.list_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_list_tools_returns_tools(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        server._connected = True
        fake_tools = [{"name": "my_tool", "description": "A test tool"}]

        async def fake_send(method, params):
            return {"result": {"tools": fake_tools}}

        with patch.object(server, "_send_request", side_effect=fake_send):
            tools = await server.list_tools()
            assert tools == fake_tools

    @pytest.mark.asyncio
    async def test_call_tool_when_not_connected(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        result = await server.call_tool("my_tool", {"arg": 1})
        assert "error" in result
        assert "未连接" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        server._connected = True
        expected_response = {"result": {"content": [{"type": "text", "text": "done"}]}}

        async def fake_send(method, params):
            assert method == "tools/call"
            assert params["name"] == "my_tool"
            return expected_response

        with patch.object(server, "_send_request", side_effect=fake_send):
            result = await server.call_tool("my_tool", {"arg": 1})
            assert result == expected_response

    @pytest.mark.asyncio
    async def test_call_tool_exception_returns_error_dict(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        server._connected = True

        with patch.object(server, "_send_request", side_effect=RuntimeError("boom")):
            result = await server.call_tool("my_tool", {})
            assert result["error"]["code"] == -32603
            assert "boom" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_list_tools_request_error_returns_empty_list(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        server._connected = True

        with patch.object(server, "_send_request", side_effect=RuntimeError("fail")):
            tools = await server.list_tools()
            assert tools == []


# =========================================================================
# MCPServer — disconnect
# =========================================================================


class TestMCPServerDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_stdio_terminates_process(self):
        server = MCPServer("test", {"transport": "stdio", "command": "uvx"})
        server._connected = True
        server.process = AsyncMock()

        await server.disconnect()
        server.process.terminate.assert_called_once()
        assert server._connected is False

    @pytest.mark.asyncio
    async def test_disconnect_http_cancels_sse_and_clears_pending(self):
        server = MCPServer("test", {"transport": "http", "url": "http://localhost/sse"})
        server._connected = True
        server._sse_task = AsyncMock()
        server._pending_requests = {}
        server._http_client = AsyncMock()

        await server.disconnect()
        assert server._connected is False
        server._sse_task.cancel.assert_called_once()
        server._http_client.aclose.assert_called_once()


# =========================================================================
# MCPClient — __init__
# =========================================================================


class TestMCPClientInit:
    def test_init_with_dict_config(self):
        config = {"mcp": {"servers": {"s1": {"enabled": True}, "s2": {"enabled": False}}}}
        client = MCPClient(config)
        assert "s1" in client.server_config
        assert "s2" in client.server_config
        assert client.servers == {}
        assert client._tool_registry == {}

    def test_init_with_none_config(self):
        client = MCPClient(None)
        assert client.server_config == {}
        assert client.servers == {}


# =========================================================================
# MCPClient — connect_all
# =========================================================================


class TestMCPClientConnectAll:
    @pytest.mark.asyncio
    async def test_connect_all_skips_disabled_servers(self):
        config = {"mcp": {"servers": {"disabled_srv": {"enabled": False}}}}
        client = MCPClient(config)
        await client.connect_all()
        assert "disabled_srv" not in client.servers

    @pytest.mark.asyncio
    async def test_connect_all_connects_enabled_server(self):
        config = {
            "mcp": {
                "servers": {
                    "my_srv": {
                        "enabled": True,
                        "transport": "stdio",
                        "command": "uvx",
                    }
                }
            }
        }
        client = MCPClient(config)

        init_response = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}})
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=init_response.encode("utf-8") + b"\n")

        with patch(
            "asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_process,
        ):
            await client.connect_all()

        assert "my_srv" in client.servers

    @pytest.mark.asyncio
    async def test_connect_all_skips_failed_connection(self):
        config = {
            "mcp": {
                "servers": {
                    "fails": {
                        "enabled": True,
                        "transport": "stdio",
                        "command": "nonexistent",
                    }
                }
            }
        }
        client = MCPClient(config)

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            await client.connect_all()

        assert "fails" not in client.servers


# =========================================================================
# MCPClient — list_all_tools / call_tool
# =========================================================================


class TestMCPClientToolMethods:
    @pytest.mark.asyncio
    async def test_list_all_tools_returns_dict(self):
        client = MCPClient({"mcp": {"servers": {}}})
        srv = MCPServer("s1", {"transport": "stdio", "command": "uvx"})
        srv._connected = True
        client.servers["s1"] = srv

        with patch.object(srv, "list_tools", new_callable=AsyncMock, return_value=[{"name": "t1"}]):
            all_tools = await client.list_all_tools()
            assert all_tools == {"s1": [{"name": "t1"}]}

    @pytest.mark.asyncio
    async def test_call_tool_server_not_found(self):
        client = MCPClient({"mcp": {"servers": {}}})
        result = await client.call_tool("nonexistent", "tool", {})
        assert result["error"]["code"] == -32601
        assert "未连接" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_call_tool_delegates_to_server(self):
        client = MCPClient({"mcp": {"servers": {}}})
        srv = MCPServer("s1", {"transport": "stdio", "command": "uvx"})
        client.servers["s1"] = srv

        expected = {"result": {"content": [{"type": "text", "text": "ok"}]}}
        with patch.object(srv, "call_tool", new_callable=AsyncMock, return_value=expected):
            result = await client.call_tool("s1", "my_tool", {"x": 1})
            assert result == expected


# =========================================================================
# MCPClient — register_to_tool_registry
# =========================================================================


class TestMCPClientRegister:
    def test_register_to_tool_registry(self):
        client = MCPClient({"mcp": {"servers": {}}})
        mock_registry = MagicMock()

        all_tools = {
            "srvA": [
                {
                    "name": "greet",
                    "description": "say hello",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                }
            ]
        }

        client.register_to_tool_registry(mock_registry, all_tools)

        mock_registry.register.assert_called_once_with(
            name="mcp_srvA_greet",
            description="[MCP:srvA] say hello",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            handler=ANY,
        )
        assert "mcp_srvA_greet" in client._tool_registry
        assert client._tool_registry["mcp_srvA_greet"]["server"] == "srvA"

    def test_register_default_schema_when_missing(self):
        client = MCPClient({"mcp": {"servers": {}}})
        mock_registry = MagicMock()

        all_tools = {
            "srvB": [
                {
                    "name": "simple",
                    "description": "no schema",
                }
            ]
        }

        client.register_to_tool_registry(mock_registry, all_tools)

        call_kwargs = mock_registry.register.call_args[1]
        assert "type" in call_kwargs["input_schema"]
        assert call_kwargs["input_schema"]["type"] == "object"
        assert "additionalProperties" in call_kwargs["input_schema"]
        assert call_kwargs["input_schema"]["additionalProperties"] is False


# =========================================================================
# MCPClient — _create_handler
# =========================================================================


class TestMCPClientCreateHandler:
    @pytest.mark.asyncio
    async def test_handler_success(self):
        client = MCPClient({"mcp": {"servers": {}}})
        srv = MCPServer("s1", {"transport": "stdio", "command": "uvx"})
        client.servers["s1"] = srv

        mcp_result = {
            "result": {
                "content": [{"type": "text", "text": "Hello world"}],
            }
        }

        with patch.object(srv, "call_tool", new_callable=AsyncMock, return_value=mcp_result):
            handler = client._create_handler("s1", "greet")
            result = await handler(name="world")

        assert result["success"] is True
        assert result["data"]["text"] == "Hello world"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_handler_error(self):
        client = MCPClient({"mcp": {"servers": {}}})
        srv = MCPServer("s1", {"transport": "stdio", "command": "uvx"})
        client.servers["s1"] = srv

        mcp_result = {
            "error": {"message": "Something went wrong"},
        }

        with patch.object(srv, "call_tool", new_callable=AsyncMock, return_value=mcp_result):
            handler = client._create_handler("s1", "failing_tool")
            result = await handler(bad_arg=42)

        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_handler_with_multiple_text_parts(self):
        client = MCPClient({"mcp": {"servers": {}}})
        srv = MCPServer("s1", {"transport": "stdio", "command": "uvx"})
        client.servers["s1"] = srv

        mcp_result = {
            "result": {
                "content": [
                    {"type": "text", "text": "Part 1"},
                    {"type": "image", "text": "skip"},
                    {"type": "text", "text": "Part 2"},
                ],
            }
        }

        with patch.object(srv, "call_tool", new_callable=AsyncMock, return_value=mcp_result):
            handler = client._create_handler("s1", "multi")
            result = await handler()

        assert result["success"] is True
        assert "Part 1" in result["data"]["text"]
        assert "Part 2" in result["data"]["text"]
        assert "skip" not in result["data"]["text"]


# =========================================================================
# MCPClient — close_all
# =========================================================================


class TestMCPClientCloseAll:
    @pytest.mark.asyncio
    async def test_close_all_disconnects_all_servers(self):
        client = MCPClient({"mcp": {"servers": {}}})
        srv_a = MCPServer("a", {"transport": "stdio", "command": "uvx"})
        srv_b = MCPServer("b", {"transport": "stdio", "command": "uvx"})
        client.servers["a"] = srv_a
        client.servers["b"] = srv_b

        with (
            patch.object(srv_a, "disconnect", new_callable=AsyncMock) as disc_a,
            patch.object(srv_b, "disconnect", new_callable=AsyncMock) as disc_b,
        ):
            await client.close_all()

        disc_a.assert_called_once()
        disc_b.assert_called_once()
        assert client.servers == {}

    @pytest.mark.asyncio
    async def test_close_all_handles_disconnect_exception(self, caplog):
        import logging

        logging.getLogger("core.mcp_client").setLevel(logging.WARNING)
        client = MCPClient({"mcp": {"servers": {}}})
        srv = MCPServer("bad", {"transport": "stdio", "command": "uvx"})
        client.servers["bad"] = srv

        with patch.object(srv, "disconnect", new_callable=AsyncMock, side_effect=RuntimeError("oops")):
            await client.close_all()

        assert "断开" in caplog.text
        assert "失败" in caplog.text
        assert client.servers == {}


# =========================================================================
# MCPClient — get_all_tools
# =========================================================================


class TestMCPClientGetAllTools:
    def test_get_all_tools_returns_registered_tools(self):
        client = MCPClient({"mcp": {"servers": {}}})
        client._tool_registry = {
            "mcp_srv_t1": {
                "name": "t1",
                "description": "tool one",
                "inputSchema": {"type": "object"},
                "server": "srv",
            }
        }

        tools = client.get_all_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "t1"
        assert tools[0]["server"] == "srv"

    def test_get_all_tools_empty(self):
        client = MCPClient({"mcp": {"servers": {}}})
        assert client.get_all_tools() == []
