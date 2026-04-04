import importlib.util
import asyncio
from .skill_registry import SkillRegistry

class SkillHandler:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    async def execute(self, skill_name: str, method: str, params: dict) -> dict:
        skill = self.registry.get_skill(skill_name)
        if not skill:
            return {"error": f"技能 {skill_name} 不存在"}
        if skill["module"] is None:
            module_path = skill["path"] / "implementation.py"
            spec = importlib.util.spec_from_file_location(skill_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
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
