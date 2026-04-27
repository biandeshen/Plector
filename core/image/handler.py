"""
图片处理主处理器
"""

import logging

from .backends import get_available_backends, get_best_backend
from .validator import validate_image_source

logger = logging.getLogger(__name__)


class ImageHandler:
    """
    图片处理主处理器

    使用方式:
        handler = ImageHandler()

        # 分析图片
        result = await handler.analyze("path/to/image.png")

        # 获取可用后端
        backends = handler.get_backends()
    """

    def __init__(self, backend_name: str | None = None):
        """
        初始化处理器

        Args:
            backend_name: 指定后端名称，None 则自动选择最佳后端
        """
        self._backend_name = backend_name
        self._backend = None

    @property
    def backend(self) -> dict | None:
        """获取当前使用的后端"""
        if self._backend is None:
            if self._backend_name:
                from .backends import get_backend

                self._backend = get_backend(self._backend_name)
            else:
                self._backend = get_best_backend()
        return self._backend

    def get_backends(self) -> list[dict]:
        """获取可用后端列表"""
        return get_available_backends()

    async def analyze(self, source: str, prompt: str | None = None) -> dict:
        """
        分析图片

        Args:
            source: 图片路径或 URL
            prompt: 自定义提示词，None 则使用默认

        Returns:
            {"success": bool, "result": str, "error": str}
        """
        # 验证来源
        is_valid, error = validate_image_source(source)
        if not is_valid:
            return {"success": False, "result": "", "error": error}

        backend = self.backend
        if not backend:
            return {"success": False, "result": "", "error": "没有可用的图片处理后端"}

        # 根据后端类型调用
        backend_type = backend.get("type")

        if backend_type == "mcp":
            return await self._call_mcp_backend(backend, source, prompt)
        elif backend_type == "skill":
            return await self._call_skill_backend(backend, source, prompt)
        else:
            return {"success": False, "result": "", "error": f"未知后端类型: {backend_type}"}

    async def _call_mcp_backend(self, backend: dict, source: str, prompt: str | None) -> dict:
        """调用 MCP 后端"""
        try:
            from core.mcp_client import get_mcp_client

            server = backend.get("server")
            tool = backend.get("tool")

            if not server or not tool:
                return {"success": False, "result": "", "error": "MCP 后端配置不完整"}

            client = get_mcp_client(server)
            if not client:
                return {"success": False, "result": "", "error": f"MCP server {server} 未连接"}

            # 构建提示词
            if not prompt:
                prompt = "详细描述这张图片的内容"

            result = await client.call_tool(
                tool,
                {
                    "image_source": source,
                    "prompt": prompt,
                },
            )

            return {"success": True, "result": result, "error": ""}

        except Exception as e:
            logger.exception("MCP 后端调用失败")
            return {"success": False, "result": "", "error": str(e)}

    async def _call_skill_backend(self, backend: dict, source: str, prompt: str | None) -> dict:
        """调用技能后端"""
        try:
            from core.skill_handler import SkillHandler

            skill_name = backend.get("skill")
            if not skill_name:
                return {"success": False, "result": "", "error": "技能后端未指定技能名"}

            handler = SkillHandler()
            result = await handler.execute(
                skill_name,
                {
                    "source": source,
                    "prompt": prompt,
                },
            )

            return {"success": True, "result": result, "error": ""}

        except Exception as e:
            logger.exception("技能后端调用失败")
            return {"success": False, "result": "", "error": str(e)}


def get_image_help() -> dict:
    """获取图片相关命令帮助"""
    from .config import IMAGE_COMMANDS

    return {
        "commands": IMAGE_COMMANDS,
        "supported_formats": list({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}),
        "max_size_mb": 20,
    }
