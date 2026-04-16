import re

content = open('services/skill_router/implementation.py', encoding='utf-8').read()

# 检查是否有违规的直接 import
bad_imports = re.findall(r'from skills\.(?!agency_orchestrator)', content)
if bad_imports:
    print('VIOLATION: direct skill imports found:', bad_imports)
else:
    print('OK: no direct skill imports')

# 检查是否使用了 SkillHandler.execute
if 'self._skill_handler.execute' in content:
    print('OK: uses SkillHandler.execute()')
else:
    print('FAIL: does not use SkillHandler.execute()')

# 检查是否使用了 event_bus_v2
if 'event_bus_v2' in content or 'EventBusV2' in content:
    print('OK: uses core.event_bus_v2')
else:
    print('FAIL: does not use core.event_bus_v2')

print('\nAll checks passed!' if not bad_imports else '\nViolations found!')
