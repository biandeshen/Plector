---
tags: [Plector, 技能规范, 开发标准]
type: standard
created: 2026-04-08
---

# Plector 技能开发规范

```markdown
---
title: Skill Development Standard
category: standards
last_updated: 2026-04-04
version: 1.0.0
related:
  - Design_Plector_v1.2.md
  - Code_Standard_Plector.md
  - PRD_Plector_v1.2.md
---

# Plector Skill Development Standard

*Version: 1.0.0*
*Updated: 2026-04-04*

> 本文档用于指导开发 Plector 技能。
> 所有新技能必须遵守以下规范，否则会被 pre-commit 钩子或 `validate_skills.py` 标记为不合格。

---

## 一、技能 vs 工具

### 判断标准：是否参与治理

| 类型 | 定义 | 数量限制 | 目录位置 |
|------|------|----------|----------|
| 技能（Skill） | 出错会影响系统稳定性或核心闭环的功能 | ≤ 15 个 | `skills/` |
| 工具（Tool） | 出错不影响系统核心流程的纯函数 | 无限制 | `tools/` |

### 判断流程

```
这个功能出错会导致系统不稳定吗？
  ├─ 是 → 放 skills/，需要 skill.json，参与治理
  └─ 否 → 放 tools/，用 @tool 装饰器，不参与治理
```

### 示例

| 功能 | 类型 | 原因 |
|------|------|------|
| health_monitor | 技能 | 出错影响闭环，参与 health 事件 |
| error_knowledge | 技能 | 出错影响错误处理闭环 |
| markdown_converter | 工具 | 纯文本转换，出错不影响核心流程 |
| web_search | 工具 | 网络请求，失败可重试，不影响系统 |
| auto_commit | 工具 | Git 操作，出错不影响 Agent 循环 |

---

## 二、技能目录结构

```
skills/<skill_name>/
├── skill.json          # 元数据（必须）
└── implementation.py   # 实现代码（必须）
```

### 目录名规范

- 全小写，下划线分隔
- 与 `skill.json` 中的 `name` 字段一致

```bash
# ✅ 正确
skills/health_monitor/
skills/error_knowledge/
skills/code_writer/

# ❌ 错误
skills/health-monitor/      # 连字符
skills/HealthMonitor/       # 大写
skills/health monitor/      # 空格
```

### 不使用分层目录

```
# ✅ Plector：扁平结构
skills/
├── health_monitor/
├── error_knowledge/
└── code_writer/

# ❌ 不使用 tier 分层（与 OpenClaw 不同）
skills/
├── tier_1_system/
│   └── health_monitor/
└── tier_2_functional/
    └── error_knowledge/
```

---

## 三、skill.json 规范

### 3.3 skill.json 必需字段

```json
{
  "name": "health_monitor",
  "description": "获取系统健康状态",
  "version": "1.0.0",
  "tier": "tier_1_system",
  "dependencies": [],
  "events_produced": ["health.degraded", "health.recovered"],
  "events_consumed": [],
  "tools": [
    {
      "name": "check_health",
      "description": "执行健康检查",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": false
      }
    }
  ]
}
```

### 3.4 字段要求

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 技能名称，唯一，与目录名一致 |
| `description` | string | ✅ | 简短描述，供 LLM 和人类阅读 |
| `version` | string | ✅ | 语义化版本号 `x.y.z` |
| `tier` | string | ✅ | 层级 |
| `dependencies` | array | ✅ | 依赖的其他技能名称列表 |
| `events_produced` | array | ✅ | 本技能发布的事件列表 |
| `events_consumed` | array | ✅ | 本技能订阅的事件列表 |
| `tools` | array | ✅ | MCP Tool 格式的工具定义 |

### tier 含义

| tier | 说明 | 典型技能 |
|------|------|----------|
| tier_0_kernel | 核心内核，系统必需 | 无（核心模块在 core/） |
| tier_1_system | 系统级，影响整体稳定性 | health_monitor |
| tier_2_functional | 功能型，提供业务能力 | error_knowledge, code_writer |
| tier_3_tool | 工具型，辅助功能 | hello_world |

### 3.5 tools 字段要求（MCP 格式）

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `tools[].name` | string | ✅ | 方法名 |
| `tools[].description` | string | ✅ | 方法描述 |
| `tools[].inputSchema` | object | ✅ | JSON Schema 格式的参数定义 |
| `tools[].inputSchema.type` | string | ✅ | 固定为 `"object"` |
| `tools[].inputSchema.properties` | object | ✅ | 参数定义 |
| `tools[].inputSchema.required` | array | ✅ | 必需参数列表 |
| `tools[].inputSchema.additionalProperties` | boolean | ✅ | 固定为 `false` |

### 完整示例

```json
{
  "name": "error_knowledge",
  "description": "记录错误并分类，存储到本地知识库",
  "version": "1.0.0",
  "tier": "tier_2_functional",
  "dependencies": [],
  "events_produced": ["error.classified", "error.stored"],
  "events_consumed": ["test.failed", "skill.failed"],
  "tools": [
    {
      "name": "store_error",
      "description": "存储错误信息到本地知识库",
      "inputSchema": {
        "type": "object",
        "properties": {
          "error": {
            "type": "string",
            "description": "错误描述"
          }
        },
        "required": ["error"],
        "additionalProperties": false
      }
    },
    {
      "name": "classify_error",
      "description": "分类错误类型，返回分类结果和置信度",
      "inputSchema": {
        "type": "object",
        "properties": {
          "error": {
            "type": "string",
            "description": "错误描述"
          }
        },
        "required": ["error"],
        "additionalProperties": false
      }
    }
  ]
}
```

---

## 四、implementation.py 规范

### 4.1 SkillHandler 类

所有技能必须实现 `SkillHandler` 类。系统通过 `skill_handler.execute()` 调用它。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康监控技能 - 获取系统健康状态

功能：
    1. 获取 CPU/内存/磁盘使用率
    2. 判断系统健康状态
    3. 发布健康事件

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import asyncio
import psutil
from core.event_bus import get_event_bus


class SkillHandler:
    """健康监控技能处理器"""

    def __init__(self):
        self.name = "health_monitor"

    async def check_health(self) -> dict:
        """
        执行健康检查

        返回:
            {"success": bool, "data": {"cpu": float, "memory": float, "status": str}, "error": str or None}
        """
        try:
            loop = asyncio.get_event_loop()
            cpu = await loop.run_in_executor(
                None, lambda: psutil.cpu_percent(interval=0)
            )
            memory = await loop.run_in_executor(
                None, lambda: psutil.virtual_memory().percent
            )
            disk = await loop.run_in_executor(
                None, lambda: psutil.disk_usage('/').percent
            )
            status = "healthy" if all(
                v < 80 for v in [cpu, memory, disk]
            ) else "degraded"

            # 发布事件
            bus = get_event_bus()
            await bus.publish(f"health.{status}", {
                "cpu": cpu, "memory": memory, "disk": disk
            })

            return {
                "success": True,
                "data": {"cpu": cpu, "memory": memory, "disk": disk, "status": status},
                "error": None
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
```

### 4.2 方法规范

- 方法名与 `skill.json` 中 `tools` 的 `name` 一致
- 返回值统一格式：`{"success": bool, "data": any, "error": str or None}`
- 异步方法使用 `async def`
- 阻塞调用使用 `run_in_executor`

```python
# ✅ 正确：方法名与 skill.json 一致
class SkillHandler:
    async def check_health(self) -> dict:  # 对应 tools[].name = "check_health"
        ...

# ❌ 错误：方法名不一致
class SkillHandler:
    async def health(self) -> dict:  # skill.json 中是 check_health
        ...
```

### 4.3 事件发布

使用 `core.event_bus.get_event_bus()`：

```python
from core.event_bus import get_event_bus

class SkillHandler:
    async def check_health(self) -> dict:
        # ... 检查逻辑 ...

        # 发布事件
        bus = get_event_bus()
        if status == "degraded":
            await bus.publish("health.degraded", {
                "cpu": cpu, "memory": memory, "disk": disk
            })
        else:
            await bus.publish("health.recovered", {
                "cpu": cpu, "memory": memory, "disk": disk
            })

        return {"success": True, "data": {...}, "error": None}
```

### 4.4 事件订阅

在 `__init__` 中订阅：

```python
from core.event_bus import get_event_bus

class SkillHandler:
    def __init__(self):
        self.name = "error_knowledge"
        # 订阅事件
        bus = get_event_bus()
        bus.subscribe("test.failed", self._on_test_failed)
        bus.subscribe("skill.failed", self._on_skill_failed)

    async def _on_test_failed(self, payload: dict):
        """处理 test.failed 事件"""
        error = payload.get("error", "unknown error")
        await self.store_error(error=error)

    async def _on_skill_failed(self, payload: dict):
        """处理 skill.failed 事件"""
        error = payload.get("error", "unknown error")
        await self.store_error(error=error)
```

### 4.5 异常处理

```python
# ✅ 正确：捕获异常，返回标准格式
async def store_error(self, error: str) -> dict:
    try:
        error_id = str(uuid.uuid4())[:8]
        # ... 存储逻辑 ...
        return {"success": True, "data": {"error_id": error_id}, "error": None}
    except Exception as e:
        logger.error(f"存储错误失败: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}

# ❌ 错误：裸 except
async def store_error(self, error: str):
    try:
        ...
    except:
        return None
```

---

## 五、与 Agent Loop 的集成

### 5.1 技能自动注册为工具

Agent Loop 会自动将技能注册为工具，LLM 通过统一的 `tool_calls` 机制调用：

```
skill.json 中的 tools
  ↓ AgentLoop._register_skills_as_tools()
  ↓ 注册到 ToolRegistry
  ↓ LLM 看到工具 schema
  ↓ LLM 返回 tool_calls
  ↓ ToolRegistry.execute()
  ↓ SkillHandler.execute()
```

### 5.2 LLM 调用格式

LLM 会生成类似以下的 tool_call：

```json
{
  "function": {
    "name": "health_monitor_check_health",
    "arguments": "{}"
  }
}
```

工具名格式：`{skill_name}_{method_name}`（`_` 分隔，符合 OpenAI 命名规范）

### 5.3 ContextBuilder 自动描述技能

ContextBuilder 会从 `skill.json` 的 `description` 字段生成技能描述，供 LLM 参考：

```
## 可用技能
- health_monitor: 获取系统健康状态，包括 CPU、内存、磁盘使用率
- error_knowledge: 记录错误并分类，存储到本地知识库
```

---

## 六、与闭环的集成

### 6.1 事件驱动

技能通过事件参与闭环，不需要直接调用其他技能：

```
test.failed 事件
  ↓ EventBus.publish()
  ↓ ClosureEngine 订阅
  ↓ 调用 error_knowledge.store_error
  ↓ error_knowledge 发布 error.stored 事件
  ↓ 继续闭环...
```

### 6.2 skill.json 中声明事件

```json
{
  "events_produced": ["error.classified", "error.stored"],
  "events_consumed": ["test.failed", "skill.failed"]
}
```

- `events_produced`：本技能发布的事件
- `events_consumed`：本技能订阅的事件

### 6.3 closed_loops.yaml 中引用

```yaml
error_record_loop:
  trigger_on: ["test.failed"]
  entry: "record_error"
  max_iterations: 2
  nodes:
    record_error:
      type: "skill"
      skill: "error_knowledge"
      method: "store_error"
      next: "classify_error"
    classify_error:
      type: "skill"
      skill: "error_knowledge"
      method: "classify_error"
      next: "end"
    end:
      type: "end"
```

---

## 七、工具函数规范（对比）

工具函数不需要 `skill.json`，使用 `@tool` 装饰器：

```python
# tools/markdown_converter.py
from core.function_calling import tool

@tool
def convert_markdown(markdown_text: str) -> str:
    """
    将 Markdown 转换为 HTML

    参数:
        markdown_text: Markdown 文本

    返回:
        HTML 字符串
    """
    import markdown
    return markdown.markdown(markdown_text)
```

### 技能 vs 工具对比

| 对比项 | 技能 | 工具 |
|--------|------|------|
| 目录 | `skills/<name>/` | `tools/<name>.py` |
| 元数据 | `skill.json`（必须） | 无 |
| 类 | `SkillHandler` | 无 |
| 装饰器 | 无 | `@tool` |
| 治理 | ✅ 健康分、淘汰 | ❌ |
| 事件 | ✅ 可发布/订阅 | ❌ |
| 数量限制 | ≤ 15 | 无限制 |
| 异步 | ✅ 支持 | ✅ 支持 |

---

## 八、创建新技能流程

### 步骤

```bash
# 1. 创建目录
mkdir -p skills/<skill_name>

# 2. 创建 skill.json
cat > skills/<skill_name>/skill.json << 'EOF'
{
  "name": "<skill_name>",
  "description": "技能描述",
  "version": "1.0.0",
  "tier": "tier_2_functional",
  "dependencies": [],
  "events_produced": [],
  "events_consumed": [],
  "tools": [
    {
      "name": "<method_name>",
      "description": "方法描述",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": false
      }
    }
  ]
}
EOF

# 3. 创建 implementation.py
cat > skills/<skill_name>/implementation.py << 'EOF'
class SkillHandler:
    """技能描述"""

    def __init__(self):
        self.name = "<skill_name>"

    async def <method_name>(self) -> dict:
        """
        方法描述

        返回:
            {"success": bool, "data": any, "error": str or None}
        """
        try:
            # 实现逻辑
            return {"success": True, "data": {}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
EOF

# 4. 验证
python -m py_compile skills/<skill_name>/implementation.py

# 5. 提交
git add skills/<skill_name>/
git commit -m "feat(<skill_name>): 添加<技能描述>"
git push
```

---

## 九、验证清单

创建或修改技能后，必须验证：

- [ ] `skill.json` 包含所有必需字段
- [ ] `name` 与目录名一致
- [ ] `tier` 值合法（`tier_0_kernel` / `tier_1_system` / `tier_2_functional` / `tier_3_tool`）
- [ ] `dependencies` 中的技能存在，无循环依赖
- [ ] `implementation.py` 定义了 `SkillHandler` 类
- [ ] 方法名与 `skill.json` 中 `tools` 的 `name` 一致
- [ ] 方法返回 `{"success": bool, "data": any, "error": str or None}` 格式
- [ ] 异步方法使用 `async def`
- [ ] 阻塞调用使用 `run_in_executor`
- [ ] 无 `print()` 调试语句
- [ ] 所有异常都有处理
- [ ] `python -m py_compile skills/<name>/implementation.py` 无语法错误
- [ ] `python scripts/validate_skills.py` 通过

### 自动验证

```bash
# 语法检查
python -m py_compile skills/health_monitor/implementation.py

# 元数据检查
python scripts/validate_skills.py

# 集成检查
python -c "
from core.skill_registry import SkillRegistry
from core.skill_handler import SkillHandler
r = SkillRegistry()
r.scan()
print(f'{len(r.skills)} skills loaded')
for name in r.skills:
    print(f'  - {name}')
"

# CLI 验证
python channels/cli.py --query "调用 health_monitor.check_health"
```

---

## 十、完整示例：health_monitor

### 目录结构

```
skills/health_monitor/
├── skill.json
└── implementation.py
```

### skill.json

```json
{
  "name": "health_monitor",
  "description": "获取系统健康状态",
  "version": "1.0.0",
  "tier": "tier_1_system",
  "dependencies": [],
  "events_produced": ["health.degraded", "health.recovered"],
  "events_consumed": [],
  "tools": [
    {
      "name": "check_health",
      "description": "执行健康检查",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": false
      }
    }
  ]
}
```

### implementation.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康监控技能 - 获取系统健康状态

功能：
    1. 获取 CPU/内存/磁盘使用率
    2. 判断系统健康状态
    3. 发布健康事件

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import asyncio
import logging

import psutil

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """健康监控技能处理器"""

    def __init__(self):
        self.name = "health_monitor"

    async def check_health(self) -> dict:
        """
        执行健康检查

        返回:
            {"success": bool, "data": {"cpu": float, "memory": float, "disk": float, "status": str}, "error": str or None}
        """
        try:
            loop = asyncio.get_event_loop()
            cpu = await loop.run_in_executor(
                None, lambda: psutil.cpu_percent(interval=0)
            )
            memory = await loop.run_in_executor(
                None, lambda: psutil.virtual_memory().percent
            )
            disk = await loop.run_in_executor(
                None, lambda: psutil.disk_usage('/').percent
            )

            status = "healthy" if all(
                v < 80 for v in [cpu, memory, disk]
            ) else "degraded"

            # 发布健康事件
            bus = get_event_bus()
            await bus.publish(f"health.{status}", {
                "cpu": cpu,
                "memory": memory,
                "disk": disk,
            })

            return {
                "success": True,
                "data": {"cpu": cpu, "memory": memory, "disk": disk, "status": status},
                "error": None,
            }
        except Exception as e:
            logger.error(f"健康检查失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}
```

---

## 十一、完整示例：error_knowledge

### 目录结构

```
skills/error_knowledge/
├── skill.json
└── implementation.py
```

### skill.json

```json
{
  "name": "error_knowledge",
  "description": "记录错误并分类，存储到本地知识库",
  "version": "1.0.0",
  "tier": "tier_2_functional",
  "dependencies": [],
  "events_produced": ["error.classified", "error.stored"],
  "events_consumed": ["test.failed", "skill.failed"],
  "tools": [
    {
      "name": "store_error",
      "description": "存储错误信息到本地知识库",
      "inputSchema": {
        "type": "object",
        "properties": {
          "error": {"type": "string", "description": "错误描述"}
        },
        "required": ["error"],
        "additionalProperties": false
      }
    },
    "classify_error": {
      "description": "分类错误类型",
      "params": {
        "error": {"type": "string", "description": "错误描述"}
      },
      "returns": {"category": "string", "confidence": "float"}
    }
  }
}
```

### implementation.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误知识技能 - 记录并分类错误

功能：
    1. 存储错误到本地知识库
    2. 分类错误类型
    3. 发布错误事件

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """错误知识技能处理器"""

    def __init__(self):
        self.name = "error_knowledge"
        self.errors_dir = Path("data/errors")
        self.errors_dir.mkdir(parents=True, exist_ok=True)

        # 订阅事件
        bus = get_event_bus()
        bus.subscribe("test.failed", self._on_test_failed)
        bus.subscribe("skill.failed", self._on_skill_failed)

    async def _on_test_failed(self, payload: dict):
        """处理 test.failed 事件"""
        error = payload.get("error", "unknown error")
        await self.store_error(error=error)

    async def _on_skill_failed(self, payload: dict):
        """处理 skill.failed 事件"""
        error = payload.get("error", "unknown error")
        await self.store_error(error=error)

    async def store_error(self, error: str) -> dict:
        """
        存储错误信息

        参数:
            error: 错误描述

        返回:
            {"success": bool, "data": {"error_id": str}, "error": str or None}
        """
        try:
            error_id = str(uuid.uuid4())[:8]
            classified = self._classify(error)
            record = {
                "id": error_id,
                "error": error,
                "timestamp": datetime.now().isoformat(),
                "classified": classified,
            }

            # 存储到文件
            file_path = self.errors_dir / f"{error_id}.json"
            with open(file_path, "w") as f:
                json.dump(record, f, indent=2)

            # 发布事件
            bus = get_event_bus()
            await bus.publish("error.stored", {"error_id": error_id, "error": error})

            return {
                "success": True,
                "data": {"error_id": error_id},
                "error": None,
            }
        except Exception as e:
            logger.error(f"存储错误失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def classify_error(self, error: str) -> dict:
        """
        分类错误类型

        参数:
            error: 错误描述

        返回:
            {"success": bool, "data": {"category": str, "confidence": float}, "error": str or None}
        """
        try:
            classified = self._classify(error)

            # 发布事件
            bus = get_event_bus()
            await bus.publish("error.classified", classified)

            return {
                "success": True,
                "data": classified,
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def _classify(self, error: str) -> dict:
        """
        内部分类逻辑

        参数:
            error: 错误描述

        返回:
            {"category": str, "confidence": float}
        """
        error_lower = error.lower()
        if "syntax" in error_lower:
            return {"category": "syntax_error", "confidence": 0.9}
        elif "timeout" in error_lower:
            return {"category": "timeout", "confidence": 0.8}
        elif "permission" in error_lower:
            return {"category": "permission", "confidence": 0.8}
        elif "connection" in error_lower:
            return {"category": "connection", "confidence": 0.7}
        else:
            return {"category": "unknown", "confidence": 0.3}
```

---


## 参考资料

- [PRD v1.2 - 技能与工具区分标准](docs/specs/PRD_Plector_v1.2.md)
- [Design v1.2 - 技能注册与执行](docs/specs/Design_Plector_v1.2.md)
- [Code Standard - 异步规范](docs/standards/Code_Standard_Plector.md)

---

## 十二、对齐标准

| 组件 | 标准 | Plector 实现 |
|------|------|-------------|
| 技能定义 | MCP Tool | `tools` + `inputSchema` |
| 工具 Schema | OpenAI Function Calling | `strict: true` + `additionalProperties: false` |
| 事件格式 | CloudEvents 1.0 | `specversion/id/source/type/time/data` |
| 错误格式 | JSON-RPC 2.0 | `jsonrpc/error.code/error.message` |
| 工具名称 | OpenAI 命名规范 | `{skill_name}_{method_name}`（`_` 分隔） |

参考：
- [MCP](https://modelcontextprotocol.io/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [CloudEvents](https://cloudevents.io/)
- [JSON-RPC 2.0](https://www.jsonrpc.org/specification)


---

 
 
## SKILL.md 规范

每个技能目录必须包含 SKILL.md 文件，对齐 Agent Skills 开放标准。

### 文件格式

\\markdown
---
name: <技能名称（必选，与 skill.json 一致）>
description: <技能描述（必选，包含触发词和使用场景）>
---

# 技能标题

## 目的
简要说明本技能解决什么问题

## 适用场景
- 场景1
- 场景2

## 执行步骤
1. 步骤一
2. 步骤二

## 成功标准
- 标准1
- 标准2

## 相关工具
- \	ool_name\：用途说明
\
### 渐进式披露

| 层级 | 内容 | Token | 加载时机 |
|------|------|-------|---------|
| 第一层 | name + description | ~100 | 始终加载 |
| 第二层 | SKILL.md 主体 | <5k | 技能相关时加载 |
| 第三层 | references/ scripts/ | 不限 | 按需加载 |

### 检查清单

- [ ] SKILL.md 存在且包含 YAML frontmatter
- [ ] name 与 skill.json 一致
- [ ] description 包含触发词和使用场景

---
