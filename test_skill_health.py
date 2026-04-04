import asyncio
from core.skill_registry import SkillRegistry
from core.skill_handler import SkillHandler

async def test():
    r = SkillRegistry()
    r.scan()
    h = SkillHandler(r)
    result = await h.execute('health_monitor', 'check_health', {})
    print(result)

asyncio.run(test())
