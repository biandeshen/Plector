from core.skill_registry import SkillRegistry
r = SkillRegistry()
r.scan()
for name, info in r.skills.items():
    tools = info['meta'].get('tools', [])
    print(f'{name}: {len(tools)} tools')
    for t in tools:
        print(f'  - {t["name"]}: {t["description"]}')
