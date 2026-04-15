"""
接口适配器
将旧版模块适配到新接口
"""
from typing import Any, Dict
from core.interfaces import Response, SkillInterface
from core.skill_loader import SkillLoader


class SkillAdapter(SkillInterface):
    """技能适配器"""
    
    def __init__(self, skill_instance: Any):
        self._skill = skill_instance
    
    @property
    def name(self) -> str:
        return getattr(self._skill, "name", self._skill.__class__.__name__)
    
    @property
    def description(self) -> str:
        return getattr(self._skill, "description", "")
    
    async def execute(self, params: Dict[str, Any]) -> Response:
        try:
            if hasattr(self._skill, "execute"):
                result = await self._skill.execute(params)
            elif hasattr(self._skill, "__call__"):
                result = await self._skill(params)
            else:
                return Response.fail("Skill has no execute method")
            
            return Response.ok(result)
        except Exception as e:
            return Response.fail(str(e))
    
    async def validate_params(self, params: Dict[str, Any]) -> bool:
        if hasattr(self._skill, "validate_params"):
            return await self._skill.validate_params(params)
        return True


class LLClientAdapter:
    """LLM 客户端适配器"""
    
    def __init__(self, llm_client: Any):
        self._client = llm_client
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs
    ) -> Response:
        try:
            result = await self._client.chat(messages, **kwargs)
            return Response.ok(result)
        except Exception as e:
            return Response.fail(str(e))
    
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        **kwargs
    ):
        try:
            async for chunk in self._client.stream_chat(messages, **kwargs):
                yield chunk
        except Exception as e:
            yield f"Error: {str(e)}"


class MemoryAdapter:
    """记忆适配器"""
    
    def __init__(self, memory_instance: Any):
        self._memory = memory_instance
    
    async def save(self, key: str, value: Any) -> Response:
        try:
            await self._memory.save(key, value)
            return Response.ok()
        except Exception as e:
            return Response.fail(str(e))
    
    async def get(self, key: str) -> Response:
        try:
            result = await self._memory.get(key)
            return Response.ok(result)
        except Exception as e:
            return Response.fail(str(e))
    
    async def search(self, query: str, limit: int = 10) -> Response:
        try:
            result = await self._memory.search(query, limit)
            return Response.ok(result)
        except Exception as e:
            return Response.fail(str(e))
