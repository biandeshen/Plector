## Plector 代码开发规范

```markdown
---
title: Code Standard
category: explanation
last_updated: 2026-04-04
---

# Plector 代码开发规范

*版本：1.0.0*
*更新：2026-04-04*
*关联文档：BRD v1.1 / PRD v1.2 / DESIGN v1.2*

---

## 一、命名规范

### 1.1 文件与目录

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 文件 | 全小写，下划线分隔 | `agent_loop.py`, `event_bus.py` |
| Skill 目录 | 全小写，下划线分隔 | `health_monitor/`, `error_knowledge/` |
| Tool 文件 | 全小写，下划线分隔 | `markdown_converter.py`, `web_search.py` |
| 配置文件 | 全小写，下划线分隔 | `closed_loops.yaml`, `config.yaml` |

注意：
- ❌ 不使用连字符 (`-`)：如 `health-monitor/`
- ✅ 使用下划线 (`_`)：如 `health_monitor/`

### 1.2 类名

首字母大写的驼峰命名法：

- ✅ `class AgentLoop`
- ✅ `class EventBus`
- ✅ `class SkillRegistry`
- ❌ `class agent_loop`
- ❌ `class AGENT_LOOP`

### 1.3 函数与方法

全小写，下划线分隔：

- ✅ `def execute_skill()`
- ✅ `def load_config()`
- ✅ `def get_tool_schemas()`
- ❌ `def executeSkill()`

### 1.4 变量名

命名应贴近含义，避免无意义单字符：

- ✅ `skill_name`, `max_iterations`, `health_score`
- ❌ `n`, `m`, `x`, `tmp`（除非作用域极小）

### 1.5 常量

全大写，下划线分隔：

- ✅ `MAX_ITERATIONS = 10`
- ✅ `DEFAULT_TIMEOUT = 30`
- ✅ `HEALTH_THRESHOLD = 0.6`

### 1.6 异常类

以 `Error` 结尾：

- ✅ `class SkillNotFoundError(Exception)`
- ✅ `class ToolExecutionError(Exception)`
- ✅ `class ClosureConfigError(Exception)`

---

## 二、项目结构规范

### 2.1 核心目录

```
plector/
├── core/                       # 核心引擎（不依赖 skills/ 和 tools/）
│   ├── __init__.py
│   ├── agent_loop.py           # ReAct 循环
│   ├── event_bus.py            # 事件总线
│   ├── skill_registry.py       # 技能注册表
│   ├── skill_handler.py        # 技能执行器
│   ├── closure_engine.py       # 闭环引擎
│   ├── context_builder.py      # 上下文构建
│   ├── function_calling.py     # 工具注册与调用
│   └── governance.py           # 技能治理
├── skills/                     # 核心技能（≤15 个）
│   └── <skill_name>/
│       ├── skill.json          # 必须
│       └── implementation.py   # 必须
├── tools/                      # 工具函数（无限制）
│   └── <tool_name>.py          # 使用 @tool 装饰器
├── channels/                   # 接入渠道
│   ├── cli.py
│   └── websocket.py
├── config/                     # 配置文件
│   ├── config.yaml
│   ├── closed_loops.yaml
│   └── profiles/
│       ├── AGENTS.md
│       ├── SOUL.md
│       └── USER.md
├── tests/                      # 单元测试
├── logs/                       # 日志（gitignore）
└── data/                       # 运行时数据（gitignore）
```

### 2.2 核心规则

- `core/` 不得依赖 `skills/` 或 `tools/`
- `skills/` 可依赖 `core/`，不得依赖其他 `skills/`（通过事件解耦）
- `tools/` 不得依赖 `skills/` 或 `core/`（纯函数）
- `channels/` 可依赖 `core/`

---

## 三、技能与工具规范

### 3.1 区分标准

**判断原则：是否参与治理**

| 类型 | 定义 | 数量限制 |
|------|------|----------|
| 技能（Skill） | 出错会影响系统稳定性或核心闭环的功能 | ≤ 15 个 |
| 工具（Tool） | 出错不影响系统核心流程的纯函数 | 无限制 |

### 3.2 技能目录结构

```
skills/<skill_name>/
├── skill.json          # 元数据（必须）
└── implementation.py   # 实现代码（必须）
```

### 3.3 skill.json 必需字段

```json
{
  "name": "health_monitor",
  "description": "获取系统健康状态",
  "version": "1.0.0",
  "tier": "tier_1_system",
  "dependencies": [],
  "events_produced": ["health.degraded", "health.recovered"],
  "events_consumed": ["health.check_request"],
  "methods": {
    "check_health": {
      "description": "执行健康检查",
      "params": {},
      "returns": {"cpu": "float", "memory": "float", "status": "string"}
    }
  }
}
```

### 3.4 SkillHandler 规范

```python
class SkillHandler:
    """技能处理器"""

    def __init__(self):
        self.name = "health_monitor"

    async def check_health(self) -> dict:
        """
        执行健康检查

        返回:
            {"cpu": float, "memory": float, "disk": float, "status": str}
        """
        # 实现逻辑
        return {"cpu": 12.0, "memory": 45.0, "disk": 30.0, "status": "healthy"}
```

### 3.5 工具函数规范

```python
from plector.core.function_calling import tool

@tool
def convert_markdown_to_html(markdown_text: str) -> str:
    """
    将 Markdown 文本转换为 HTML

    参数:
        markdown_text: Markdown 格式的文本

    返回:
        HTML 格式的字符串
    """
    import markdown
    return markdown.markdown(markdown_text)
```

---

## 四、事件规范

### 4.1 事件命名

格式：`<领域>.<动作>`

命名规则：
1. 全部小写
2. 用点号分隔领域和动作
3. 动作用过去式（表示已完成的事件）

领域列表：

| 领域 | 用途 | 示例 |
|------|------|------|
| health | 系统健康 | `health.degraded`, `health.recovered` |
| error | 错误处理 | `error.classified`, `error.stored` |
| skill | 技能管理 | `skill.failed`, `skill.eliminate.proposal` |
| test | 测试相关 | `test.failed`, `test.passed` |
| closure | 闭环执行 | `closure.completed`, `closure.failed` |
| code | 代码相关 | `code.written`, `code.analyzed` |

正确示例：
```
health.degraded      ✅
error.classified     ✅
test.failed          ✅
```

错误示例：
```
HealthDegraded       ❌ 驼峰命名
health_degraded      ❌ 下划线命名
HEALTH.DEGRADED      ❌ 全大写
```

### 4.2 事件发布

```python
from core.event_bus import get_event_bus

bus = get_event_bus()
await bus.publish("health.degraded", {"cpu": 85.0, "memory": 90.0})
```

### 4.3 事件订阅

```python
bus = get_event_bus()
bus.subscribe("health.degraded", self._on_health_degraded)
bus.subscribe("skill.*", self._on_any_skill_event)  # 通配符
```

---

## 五、闭环配置规范

### 5.1 closed_loops.yaml 结构

```yaml
loop_name:
  trigger_on: ["event.name"]        # 触发事件列表
  entry: "first_node"               # 入口节点
  max_iterations: 5                 # 最大迭代次数
  nodes:
    first_node:
      type: "skill"                 # skill / condition / end
      skill: "skill_name"
      method: "method_name"
      next: "second_node"           # 下一个节点
    second_node:
      type: "condition"
      skill: "skill_name"
      method: "method_name"
      transitions:
        key1: "node_a"
        key2: "node_b"
    node_a:
      type: "end"
```

### 5.2 节点类型

| 类型 | 说明 | 必需字段 |
|------|------|----------|
| `skill` | 调用技能 | `skill`, `method`, `next` |
| `condition` | 条件分支 | `skill`, `method`, `transitions` |
| `end` | 结束节点 | 无 |

---

## 六、注释规范

### 6.1 文件头注释

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能名称 - 功能描述

功能：
    1. 功能点1
    2. 功能点2

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""
```

### 6.2 函数注释

```python
async def execute(skill_name: str, method: str, params: dict) -> dict:
    """
    执行技能方法

    参数:
        skill_name: 技能名称
        method: 方法名
        params: 参数字典

    返回:
        {"success": bool, "result": any, "error": str or None}

    示例:
        >>> result = await handler.execute("health_monitor", "check_health", {})
        >>> print(result["result"]["status"])
        "healthy"
    """
```

### 6.3 行内注释

注释应解释**为什么**，而不是**是什么**：

- ❌ `i += 1  # i 加 1`
- ✅ `i += 1  # 跳过已处理的节点`

### 6.4 TODO 注释

```python
# TODO(v1.1): 添加缓存支持
# FIXME: 临时解决方案，需要重构
# NOTE: 设计参考了 NanoBot 的 ReAct 循环
```

---

## 七、错误处理

### 7.1 技能调用失败

```python
# ✅ 返回标准错误格式，不抛异常
async def execute(self, skill_name: str, method: str, params: dict) -> dict:
    skill = self.registry.get_skill(skill_name)
    if not skill:
        return {"error": f"技能 {skill_name} 不存在"}
    try:
        result = await func(**params)
        return {"result": result}
    except Exception as e:
        logger.error(f"技能 {skill_name}.{method} 执行失败: {e}", exc_info=True)
        return {"error": str(e)}
```

### 7.2 工具调用失败

```python
# ✅ 返回错误信息，Agent Loop 继续运行
async def execute(self, tool_call: dict) -> dict:
    name = tool_call["function"]["name"]
    tool = self._tools.get(name)
    if not tool:
        return {"error": f"工具 {name} 不存在"}
    try:
        result = tool["handler"](**arguments)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
```

### 7.3 异常捕获原则

- 优先捕获具体异常，避免裸 `except`
- 保留原始异常信息（`from e`）
- 日志记录后重新抛出或返回错误

---

## 八、异步规范

### 8.1 阻塞调用

所有阻塞调用必须放到线程池：

```python
# ✅ 正确
import asyncio
loop = asyncio.get_event_loop()
cpu = await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=1))

# ❌ 错误：阻塞事件循环
cpu = psutil.cpu_percent(interval=1)
```

### 8.2 异步函数

- I/O 操作使用 `async def`
- 同步函数调用异步函数时使用 `asyncio.run()`
- 不要在异步函数中使用 `time.sleep()`，使用 `asyncio.sleep()`

---

## 九、代码布局

### 9.1 导入顺序

```python
# 1. 标准库
import os
import sys
import json

# 2. 第三方库
import yaml
from pathlib import Path

# 3. 本地模块
from core.event_bus import get_event_bus
from core.skill_registry import SkillRegistry
```

### 9.2 行长度

每行最多 120 字符。

### 9.3 空行

| 场景 | 空行数 |
|------|--------|
| 模块之间 | 2 |
| 类之间 | 2 |
| 类内方法之间 | 1 |

### 9.4 函数长度

单个函数不超过 50 行。

### 9.5 参数数量

参数不超过 5 个，超过时使用 dataclass：

```python
from dataclasses import dataclass

@dataclass
class ExecuteParams:
    skill_name: str
    method: str
    params: dict
    timeout: int = 30
```

---

## 十、Git 提交规范

### 10.1 提交信息格式

```
<类型>(<范围>): <描述>

[可选正文]
```

### 10.2 类型

| 类型 | 描述 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| refactor | 重构 |
| test | 测试相关 |
| chore | 构建/工具相关 |

### 10.3 示例

```
feat(closure_engine): 添加闭环执行引擎

- 实现条件图解析
- 支持 skill/condition/end 三种节点类型
- 集成事件总线自动触发

Closes: #123
```

---

## 十一、验证清单

提交代码前必须验证：

- [ ] Python 语法检查：`python -m py_compile <file>.py`
- [ ] 无 `print()` 调试语句
- [ ] 所有异常都有处理
- [ ] 阻塞调用使用 `run_in_executor`
- [ ] 注释与代码同步
- [ ] 命名符合规范
- [ ] 函数不超过 50 行
- [ ] 单元测试通过

---

## 参考资料

- [PEP 8](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [NanoBot](https://github.com/HKUDS/NanoBot)

---

*本规范会持续更新。*
```

---
