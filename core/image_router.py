import logging

from .skill_handler import SkillHandler

logger = logging.getLogger(__name__)


class ImageRouter:
    """图片识别请求路由，从 AgentLoop 中分离出来"""

    def __init__(self, skill_handler: SkillHandler):
        self.skill_handler = skill_handler

    async def handle(self, user_input: str) -> str | None:
        """处理图片识别命令，如果不是图片请求则返回 None"""
        from core.image_handler import (
            get_available_backends,
            get_best_backend,
            get_image_help,
            parse_image_command,
            validate_image_path,
        )

        parsed = parse_image_command(user_input)
        if not parsed:
            return None

        prompt = parsed["prompt"]
        image_path = parsed["image_path"]

        if image_path in ["help", "帮助", "?"]:
            return get_image_help()

        if image_path in ["list", "列表", "后端"]:
            backends = get_available_backends()
            if not backends:
                return "没有可用的图片识别后端"
            lines = ["可用的图片识别后端："]
            for b in backends:
                lines.append(f"  - {b['name']} ({b['type']}, 优先级: {b['priority']})")
            return "\n".join(lines)

        is_valid, error_msg = validate_image_path(image_path)
        if not is_valid:
            return error_msg

        backend = get_best_backend()
        if not backend:
            return "没有可用的图片识别后端，请先配置 MCP Server 或 Skill"

        return await self._execute_backend(backend, prompt, image_path)

    async def _execute_backend(self, backend: dict, prompt: str, image_path: str) -> str:
        """Execute image recognition via the selected backend."""
        try:
            if backend["type"] == "mcp":
                result = await self.skill_handler.execute(
                    backend["server"],
                    backend["tool"],
                    {"prompt": prompt, "image_source": image_path},
                )
            elif backend["type"] == "skill":
                result = await self.skill_handler.execute(
                    backend["skill"],
                    backend["tool"],
                    {"prompt": prompt, "image_source": image_path},
                )
            else:
                return f"未知的后端类型: {backend['type']}"

            if result.get("success"):
                return result.get("result", {}).get("data", "")  # type: ignore[no-any-return]
            else:
                return f"图片识别失败: {result.get('error', '未知错误')}"

        except Exception as e:
            return f"图片识别出错: {e!s}"
