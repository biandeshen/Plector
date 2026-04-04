import asyncio
from core.skill_registry import SkillRegistry
from core.skill_handler import SkillHandler

async def test():
    r = SkillRegistry()
    r.scan()
    h = SkillHandler(r)
    result = await h.execute('error_knowledge', 'store_error', {'error': 'test error from e2e'})
    print(result)

asyncio.run(test())
