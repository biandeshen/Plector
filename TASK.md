# TASK.md - 修复 Skill Router 架构违规

## 当前问题

`services/skill_router/implementation.py` 直接 import 了其他技能：

```python
from skills.self_improver.implementation import ...
from skills.context_refresher.implementation import ...
from skills.memory.implementation import ...
```

**这是架构违规**。技能间必须通过 `SkillHandler.execute()` 或 `event_bus` 通信，不能直接 import。

## 必须满足的条件

1. **不能直接 import** 其他技能的 `implementation.py`
2. **必须通过** `self._skill_handler.execute("技能名", "方法", {参数})` 调用
3. event_bus 用 `core.event_bus_v2`（生产路径）

## 验收检查

运行：
```bash
python -c "
import re
content = open('services/skill_router/implementation.py').read()
bad = re.findall(r'from skills\.(?!agency_orchestrator)', content)
if bad:
    print('VIOLATION: direct skill imports found:', bad)
else:
    print('OK: no direct skill imports')
"
```
