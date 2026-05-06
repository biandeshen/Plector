import asyncio
import importlib.util
import logging
from pathlib import Path

from .skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillHandler:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    async def execute(self, skill_name: str, method: str, params: dict) -> dict:
        skill = self.registry.get_skill(skill_name)
        if not skill:
            return {"error": f"技能 {skill_name} 不存在"}
        if skill["module"] is None:
            module_path = skill["path"] / "implementation.py"
            resolved = module_path.resolve()
            skills_root = Path("skills").resolve()
            try:
                resolved.relative_to(skills_root)
            except ValueError as err:
                raise ValueError(f"模块路径 {resolved} 超出 skills 目录范围") from err
            if not resolved.exists():
                raise FileNotFoundError(f"技能 {skill_name} 的 implementation.py 不存在")
            logger.info(f"加载技能模块: {skill_name} 来自 {resolved}")
            spec = importlib.util.spec_from_file_location(skill_name, resolved)
            module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            skill["module"] = module
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
        return {"result": result}
