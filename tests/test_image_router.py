from unittest.mock import AsyncMock, patch

import pytest

from core.image_router import ImageRouter
from core.skill_handler import SkillHandler


@pytest.fixture
def skill_handler():
    return SkillHandler(None)


@pytest.fixture
def router(skill_handler):
    return ImageRouter(skill_handler)


@pytest.mark.asyncio
async def test_handle_non_image_returns_none(router):
    """非图片输入应返回 None"""
    with patch("core.image_handler.parse_image_command", return_value=None):
        result = await router.handle("你好，今天天气怎么样？")
        assert result is None


@pytest.mark.asyncio
async def test_handle_help_command(router):
    """帮助命令应返回帮助文本"""
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "", "image_path": "help"}),
        patch("core.image_handler.get_image_help", return_value="图片识别帮助文本"),
    ):
        result = await router.handle("识别图片 help")
        assert "帮助" in result


@pytest.mark.asyncio
async def test_handle_list_backends(router):
    """列出后端命令应返回后端列表"""
    backends = [
        {"name": "minimax", "type": "mcp", "priority": 10},
        {"name": "openai_vision", "type": "skill", "priority": 5},
    ]
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "", "image_path": "list"}),
        patch("core.image_handler.get_available_backends", return_value=backends),
    ):
        result = await router.handle("识别图片 list")
        assert "minimax" in result
        assert "openai_vision" in result


@pytest.mark.asyncio
async def test_handle_list_backends_empty(router):
    """无后端时空列表命令应返回提示"""
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "", "image_path": "list"}),
        patch("core.image_handler.get_available_backends", return_value=[]),
    ):
        result = await router.handle("识别图片 list")
        assert "没有" in result


@pytest.mark.asyncio
async def test_handle_invalid_path(router):
    """无效路径应返回错误消息"""
    with (
        patch(
            "core.image_handler.parse_image_command", return_value={"prompt": "描述", "image_path": "/invalid/path.jpg"}
        ),
        patch("core.image_handler.validate_image_path", return_value=(False, "文件不存在")),
    ):
        result = await router.handle("识别图片 /invalid/path.jpg")
        assert "文件不存在" in result


@pytest.mark.asyncio
async def test_handle_no_backend_available(router):
    """无可用后端应返回提示"""
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "描述", "image_path": "test.jpg"}),
        patch("core.image_handler.validate_image_path", return_value=(True, "")),
        patch("core.image_handler.get_best_backend", return_value=None),
    ):
        result = await router.handle("识别图片 test.jpg")
        assert "没有" in result


@pytest.mark.asyncio
async def test_handle_mcp_backend_success(router, skill_handler):
    """MCP 后端成功执行应返回结果数据"""
    skill_handler.execute = AsyncMock(return_value={"success": True, "result": {"data": "这是一只猫"}})
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "描述", "image_path": "cat.jpg"}),
        patch("core.image_handler.validate_image_path", return_value=(True, "")),
        patch(
            "core.image_handler.get_best_backend",
            return_value={"type": "mcp", "server": "minimax", "tool": "understand_image"},
        ),
    ):
        result = await router.handle("识别图片 cat.jpg")
        assert result == "这是一只猫"


@pytest.mark.asyncio
async def test_handle_skill_backend_success(router, skill_handler):
    """Skill 后端成功执行应返回结果数据"""
    skill_handler.execute = AsyncMock(return_value={"success": True, "result": {"data": "风景照片"}})
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "描述", "image_path": "landscape.jpg"}),
        patch("core.image_handler.validate_image_path", return_value=(True, "")),
        patch(
            "core.image_handler.get_best_backend", return_value={"type": "skill", "skill": "vision", "tool": "analyze"}
        ),
    ):
        result = await router.handle("识别图片 landscape.jpg")
        assert result == "风景照片"


@pytest.mark.asyncio
async def test_handle_backend_failure(router, skill_handler):
    """后端返回失败应返回错误消息"""
    skill_handler.execute = AsyncMock(return_value={"success": False, "error": "API 调用超时"})
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "描述", "image_path": "cat.jpg"}),
        patch("core.image_handler.validate_image_path", return_value=(True, "")),
        patch(
            "core.image_handler.get_best_backend",
            return_value={"type": "mcp", "server": "minimax", "tool": "understand_image"},
        ),
    ):
        result = await router.handle("识别图片 cat.jpg")
        assert "失败" in result
        assert "API 调用超时" in result


@pytest.mark.asyncio
async def test_handle_execution_exception(router, skill_handler):
    """后端抛出异常应返回错误消息"""
    skill_handler.execute = AsyncMock(side_effect=RuntimeError("连接错误"))
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "描述", "image_path": "cat.jpg"}),
        patch("core.image_handler.validate_image_path", return_value=(True, "")),
        patch(
            "core.image_handler.get_best_backend",
            return_value={"type": "mcp", "server": "minimax", "tool": "understand_image"},
        ),
    ):
        result = await router.handle("识别图片 cat.jpg")
        assert "出错" in result
        assert "连接错误" in result


@pytest.mark.asyncio
async def test_handle_unknown_backend_type(router, skill_handler):
    """未知后端类型应返回错误消息"""
    with (
        patch("core.image_handler.parse_image_command", return_value={"prompt": "描述", "image_path": "cat.jpg"}),
        patch("core.image_handler.validate_image_path", return_value=(True, "")),
        patch(
            "core.image_handler.get_best_backend", return_value={"type": "unknown_backend", "server": "x", "tool": "y"}
        ),
    ):
        result = await router.handle("识别图片 cat.jpg")
        assert "未知的后端类型" in result
