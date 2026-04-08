---
tags: [Plector, 代码规范, 开发标准]
type: standard
created: 2026-04-08
---

# Plector 代码开发规范（完整版）

```markdown
---
title: Code Standard
category: standards
last_updated: 2026-04-04
version: 1.0.0
related:
  - BRD_Plector_v1.1.md
  - PRD_Plector_v1.2.md
  - Design_Plector_v1.2.md
  - Naming_Convention_Plector.md
---

# Plector Code Standard

*Version: 1.0.0*
*Updated: 2026-04-04*

---

## 一、命名规范

### 1.1 文件与目录

| 类型 | 规范 | 示例 |
|------|------|------|
| Python 文件 | 全小写，下划线分隔 | `agent_loop.py`, `event_bus.py` |
| Skill 目录 | 全小写，下划线分隔 | `health_monitor/`, `error_knowledge/` |
| Tool 文件 | 全小写，下划线分隔 | `markdown_converter.py`, `web_search.py` |
| 配置文件 | 全小写，下划线分隔 | `closed_loops.yaml`, `config.yaml` |
| 测试文件 | `test_` 前缀 | `test_event_bus.py`, `test_agent_loop.py` |

注意：
- ❌ 不使用连字符 (`-`)
- ✅ 使用下划线 (`_`)
- ❌ 不使用空格
- ❌ 不使用大写字母

### 1.2 类名

首字母大写的驼峰命名法：

```python
# ✅ 正确
class AgentLoop
class EventBus
class SkillRegistry
class ClosureEngine
class ToolExecutionError

# ❌ 错误
class agent_loop
class AGENT_LOOP
class eventbus
```

### 1.3 函数与方法

全小写，下划线分隔：

```python
# ✅ 正确
def execute_skill()
def load_config()
def get_tool_schemas()
def _register_skills_as_tools()  # 私有方法

# ❌ 错误
def executeSkill()
def ExecuteSkill()
def getToolSchemas()
```

### 1.4 变量名

命名应贴近含义，避免无意义单字符：

```python
# ✅ 正确
skill_name = "health_monitor"
max_iterations = 10
health_score = 0.85
error_message = "技能不存在"

# ❌ 错误（除非作用域极小）
n = 10
m = "health_monitor"
x = 0.85
tmp = "技能不存在"
```

### 1.5 常量

全大写，下划线分隔：

```python
# ✅ 正确
MAX_ITERATIONS = 10
DEFAULT_TIMEOUT = 30
HEALTH_THRESHOLD = 0.6
REQUIRED_SKILL_FIELDS = ["name", "description", "version", "tier"]

# ❌ 错误
maxIterations = 10
default_timeout = 30
```

### 1.6 异常类

以 `Error` 结尾，继承 `Exception`：

```python
# ✅ 正确
class SkillNotFoundError(Exception):
    pass

class ToolExecutionError(Exception):
    pass

class ClosureConfigError(Exception):
    pass

# ❌ 错误
class SkillNotFound(Exception):  # 缺少 Error
    pass

class skill_not_found(Exception):  # 非驼峰
    pass
```

### 1.7 工具名称

- 格式：`{skill_name}_{method_name}`
- 示例：`health_monitor_check_health`
- ❌ 不使用 `.` 分隔：`health_monitor.check_health`
- 原因：OpenAI Function Calling 不允许 `.` 在工具名中

---

## 二、项目结构

### 2.1 核心目录

```
plector/
├── core/                       # 核心引擎
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
│       ├── skill.json
│       └── implementation.py
├── tools/                      # 工具函数（无限制）
│   └── <tool_name>.py
├── channels/                   # 接入渠道
│   ├── __init__.py
│   ├── cli.py
│   └── websocket.py
├── config/                     # 配置文件
│   ├── config.yaml
│   ├── closed_loops.yaml
│   └── profiles/
│       ├── AGENTS.md
│       ├── SOUL.md
│       └── USER.md
├── docs/                       # 文档
│   ├── specs/                  # 产品规格
│   ├── standards/              # 规范
│   ├── reports/                # 报告
│   └── dev/                    # 开发文档
├── tests/                      # 单元测试
├── scripts/                    # 工具脚本
│   ├── check_skills.py
│   └── validate_skills.py
├── logs/                       # 日志（gitignore）
├── data/                       # 运行时数据（gitignore）
├── CLAUDE.md                   # Claude Code 行为规则
├── README.md
├── requirements.txt
├── .gitignore
└── .pre-commit-config.yaml
```

### 2.2 依赖方向约束

```
core/     → 不依赖 skills/、tools/
skills/   → 可依赖 core/，不依赖其他 skills/
tools/    → 不依赖 skills/、core/
channels/ → 可依赖 core/
```

违反依赖方向的 import 必须在提交前修复。

---

## 三、导入规范

### 3.1 导入顺序

```python
# 1. 标准库
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

# 2. 第三方库
import yaml
import psutil

# 3. 本地模块
from core.event_bus import get_event_bus
from core.skill_registry import SkillRegistry
from core.skill_handler import SkillHandler
```

### 3.2 导入规则

```python
# ✅ 每行一个导入
import os
import sys

# ❌ 不在同一行导入多个
import os, sys

# ✅ 使用 from...import 导入具体对象
from core.event_bus import get_event_bus, EventBus

# ❌ 避免 from x import *
from core.event_bus import *
```

### 3.3 相对导入

`core/` 内部模块之间使用相对导入：

```python
# core/agent_loop.py
from .skill_registry import SkillRegistry
from .skill_handler import SkillHandler
from .event_bus import get_event_bus
```

`skills/` 导入 `core/` 使用绝对导入：

```python
# skills/health_monitor/implementation.py
from core.event_bus import get_event_bus
```

---

## 四、函数设计

### 4.1 函数长度

单个函数不超过 **50 行**。超过时拆分为多个小函数。

```python
# ✅ 正确：拆分
async def execute_loop(self, loop_def, payload):
    current_node = loop_def["entry"]
    context = {"payload": payload}
    for _ in range(loop_def.get("max_iterations", 10)):
        node = loop_def["nodes"][current_node]
        action = self._get_node_action(node)
        current_node = action(node, context)
        if current_node is None:
            break

def _get_node_action(self, node):
    actions = {
        "skill": self._execute_skill_node,
        "condition": self._execute_condition_node,
        "end": self._execute_end_node,
    }
    return actions.get(node["type"], self._execute_end_node)
```

### 4.2 参数数量

参数不超过 **5 个**。超过时使用 dataclass：

```python
# ✅ 正确：dataclass 封装
from dataclasses import dataclass

@dataclass
class ExecuteParams:
    skill_name: str
    method: str
    params: dict
    timeout: int = 30
    retry_count: int = 0

async def execute(self, params: ExecuteParams) -> dict:
    ...

# ❌ 错误：参数过多
async def execute(self, skill_name, method, params, timeout, retry_count, callback, context):
    ...
```

### 4.3 返回值格式

统一返回 `dict`，包含 `success`、`data`、`error` 字段：

```python
# ✅ 正确
def check_health(self) -> dict:
    return {
        "success": True,
        "data": {"cpu": 12.0, "memory": 45.0, "status": "healthy"},
        "error": None
    }

def check_health_failed(self) -> dict:
    return {
        "success": False,
        "data": None,
        "error": "psutil 未安装"
    }

# ❌ 错误：返回格式不一致
def check_health(self):
    return {"cpu": 12.0}  # 缺少 success/error

def check_health_failed(self):
    return False  # 返回 bool，格式不一致
```

### 4.4 异步函数

- I/O 操作使用 `async def`
- 同步函数调用异步函数时使用 `asyncio.run()`
- 不要在异步函数中使用 `time.sleep()`，使用 `asyncio.sleep()`

```python
# ✅ 正确
async def check_health(self) -> dict:
    loop = asyncio.get_event_loop()
    cpu = await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0))
    return {"success": True, "data": {"cpu": cpu}, "error": None}

# ❌ 错误：阻塞事件循环
async def check_health(self) -> dict:
    cpu = psutil.cpu_percent(interval=1)  # 阻塞 1 秒
    return {"success": True, "data": {"cpu": cpu}, "error": None}
```

---

## 五、错误处理

### 5.1 异常捕获原则

- 优先捕获具体异常，避免裸 `except`
- 保留原始异常信息
- 日志记录后返回错误格式

```python
# ✅ 正确：捕获具体异常
async def execute(self, skill_name: str, method: str, params: dict) -> dict:
    skill = self.registry.get_skill(skill_name)
    if not skill:
        return {"success": False, "data": None, "error": f"技能 {skill_name} 不存在"}
    try:
        result = await func(**params)
        return {"success": True, "data": result, "error": None}
    except TypeError as e:
        return {"success": False, "data": None, "error": f"参数错误: {e}"}
    except Exception as e:
        logger.error(f"技能 {skill_name}.{method} 执行失败: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}

# ❌ 错误：裸 except
async def execute(self, skill_name, method, params):
    try:
        result = await func(**params)
        return result
    except:
        return None  # 隐藏了所有错误
```

### 5.2 异常链

```python
# ✅ 正确：保留原始异常
try:
    config = yaml.safe_load(config_path.read_text())
except yaml.YAMLError as e:
    raise ClosureConfigError(f"配置文件解析失败: {e}") from e
```

### 5.3 日志

```python
import logging

logger = logging.getLogger(__name__)

# ✅ 正确
logger.info(f"技能 {skill_name} 注册成功")
logger.error(f"技能 {skill_name}.{method} 执行失败: {e}", exc_info=True)
logger.warning(f"技能 {skill_name} 健康分过低: {score}")

# ❌ 错误：使用 print
print(f"技能 {skill_name} 注册成功")
```

---

## 六、注释规范

### 6.1 文件头注释

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
```

### 6.2 类注释

```python
class AgentLoop:
    """自主决策循环，实现 ReAct 模式

    职责：
        - 管理 LLM 调用
        - 执行工具调用
        - 结果回填
        - 循环控制
    """
```

### 6.3 函数注释

```python
async def execute(self, skill_name: str, method: str, params: dict) -> dict:
    """
    执行技能方法

    参数:
        skill_name: 技能名称
        method: 方法名
        params: 参数字典

    返回:
        {"success": bool, "data": any, "error": str or None}

    示例:
        >>> result = await handler.execute("health_monitor", "check_health", {})
        >>> print(result["data"]["status"])
        "healthy"
    """
```

### 6.4 行内注释

注释应解释**为什么**，而不是**是什么**：

```python
# ✅ 正确
i += 1  # 跳过已处理的节点
cpu = psutil.cpu_percent(interval=0)  # interval=0 避免阻塞事件循环
self.health_scores[skill_name] = 0.9 * old + 0.1 * new  # 指数滑动平均

# ❌ 错误
i += 1  # i 加 1
cpu = psutil.cpu_percent(interval=0)  # 获取 CPU 使用率
```

### 6.5 TODO 注释

```python
# TODO(v1.1): 添加缓存支持
# TODO(v1.2): 支持 Redis 后端
# FIXME: 临时解决方案，需要重构
# NOTE: 设计参考了 NanoBot 的 ReAct 循环
# HACK: 工作区限制，后续需要修改
```

---

## 七、代码布局

### 7.1 缩进

使用 4 个空格：

```python
# ✅ 正确
foo = long_function_name(
    var_one,
    var_two,
    var_three,
)

config = {
    "name": "test",
    "version": "1.0",
}

# ❌ 错误：混用 Tab 和空格
foo = long_function_name(
 var_one,  # Tab
    var_two,  # 空格
)
```

### 7.2 行长度

每行最多 **120 字符**。超过时使用括号续行：

```python
# ✅ 正确
result = await self.skill_handler.execute(
    skill_name=node["skill"],
    method=node["method"],
    params=context.get("last_result", {}),
)

# ❌ 错误：超过 120 字符
result = await self.skill_handler.execute(skill_name=node["skill"], method=node["method"], params=context.get("last_result", {}))
```

### 7.3 空行

| 场景 | 空行数 |
|------|--------|
| 模块之间（import 后） | 2 |
| 类之间 | 2 |
| 类内方法之间 | 1 |
| 函数之间 | 2 |

```python
import os
import sys

from core.event_bus import get_event_bus  # ← import 后空 2 行


class AgentLoop:  # ← 类前空 2 行
    """自主决策循环"""

    def __init__(self, config: dict = None):  # ← 方法前空 1 行
        ...

    async def run(self, user_input: str) -> str:  # ← 方法间空 1 行
        ...


class EventBus:  # ← 类间空 2 行
    """事件总线"""
    ...
```

---

## 八、技能与工具规范

### 8.1 区分标准

**判断原则：是否参与治理**

| 类型 | 定义 | 数量限制 |
|------|------|----------|
| 技能（Skill） | 出错会影响系统稳定性或核心闭环 | ≤ 15 个 |
| 工具（Tool） | 出错不影响系统核心流程的纯函数 | 无限制 |

### 8.2 技能目录结构

```
skills/<skill_name>/
├── skill.json          # 元数据（必须）
└── implementation.py   # 实现代码（必须）
```

### 8.3 skill.json 必需字段

```json
{
  "name": "health_monitor",
  "description": "获取系统健康状态",
  "version": "1.0.0",
  "tier": "tier_1_system",
  "dependencies": [],
  "events_produced": ["health.degraded", "health.recovered"],
  "events_consumed": [],
  "methods": {
    "check_health": {
      "description": "执行健康检查",
      "params": {},
      "returns": {"cpu": "float", "memory": "float", "status": "string"}
    }
  }
}
```

### 8.4 SkillHandler 规范

```python
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
            return {
                "success": True,
                "data": {"cpu": cpu, "memory": memory, "disk": disk, "status": status},
                "error": None
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
```

### 8.5 工具函数规范

```python
from plector.core.function_calling import tool

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

### 8.6 对齐标准

| 组件 | 标准 | 说明 |
|------|------|------|
| 技能定义 | MCP Tool 格式 | `tools` + `inputSchema` |
| 工具 Schema | OpenAI Function Calling | `strict: true` + `additionalProperties: false` |
| 事件格式 | CloudEvents 1.0 | `specversion/id/source/type/time/data` |
| 错误格式 | JSON-RPC 2.0 | `jsonrpc/error.code/error.message` |

---

## 九、事件规范

### 9.1 命名格式

`<domain>.<action>`

规则：

1. 全部小写
2. 点号分隔领域和动作
3. 动作用过去式

### 9.2 领域列表

| 领域 | 用途 | 示例 |
|------|------|------|
| health | 系统健康 | `health.degraded`, `health.recovered` |
| error | 错误处理 | `error.classified`, `error.stored` |
| skill | 技能管理 | `skill.failed`, `skill.eliminate.proposal` |
| test | 测试相关 | `test.failed`, `test.passed` |
| closure | 闭环执行 | `closure.completed`, `closure.failed` |
| code | 代码相关 | `code.written`, `code.analyzed` |

### 9.3 事件发布

```python
from core.event_bus import get_event_bus

bus = get_event_bus()
await bus.publish("health.degraded", {
    "cpu": 85.0,
    "memory": 90.0,
    "timestamp": time.time()
})
```

### 9.4 事件订阅

```python
bus = get_event_bus()
bus.subscribe("health.degraded", self._on_health_degraded)
bus.subscribe("skill.*", self._on_any_skill_event)  # 通配符
```

---

## 十、Git 提交规范

### 10.1 原子提交

- 每完成一个可独立验证的功能点后，**立即提交**
- 提交前必须运行验证（见 10.4）
- 确保所有改动已 `git add`

### 10.2 提交信息格式

```
<type>(<scope>): <subject>

[可选 body]

[可选 footer]
```

**type**：

| 类型 | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式调整（不影响功能） |
| refactor | 重构（无功能变化） |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建/工具相关 |

**scope**：模块名，如 `core`, `health_monitor`, `closure_engine`

**subject**：简短描述，不超过 50 字符

**示例**：

```
feat(closure_engine): 添加闭环执行引擎

- 实现条件图解析
- 支持 skill/condition/end 三种节点类型
- 集成事件总线自动触发
```

### 10.3 提交后操作

- 提交成功后执行 `git push`（除非用户要求暂缓）

### 10.4 提交前检查清单

```
- [ ] 所有修改文件已保存
- [ ] python -m py_compile <file>.py（无语法错误）
- [ ] 无 print() 调试语句
- [ ] 所有异常都有处理
- [ ] 阻塞调用使用 run_in_executor
- [ ] 函数不超过 50 行
- [ ] 参数不超过 5 个
- [ ] 导入顺序正确（标准库→第三方→本地）
- [ ] 命名符合规范
- [ ] 单元测试通过（如果有）
```

---

## 十一、Pre-commit 配置

### 11.1 安装

```bash
pip install pre-commit
pre-commit install
```

### 11.2 .pre-commit-config.yaml

```yaml
repos:
  - repo: local
    hooks:
      - id: check-syntax
        name: Check Python syntax
        entry: python scripts/check_skills.py
        language: system
        files: ^skills/.*\.py$
      - id: validate-skill-json
        name: Validate skill.json
        entry: python scripts/validate_skills.py
        language: system
        files: ^skills/.*/skill\.json$
```

### 11.3 scripts/check_skills.py

```python
#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def main():
    errors = 0
    for impl in Path("skills").rglob("implementation.py"):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(impl)],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"Syntax error in {impl}:")
            print(result.stderr.decode())
            errors += 1
    sys.exit(errors)

if __name__ == "__main__":
    main()
```

### 11.4 scripts/validate_skills.py

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "name", "description", "version", "tier",
    "dependencies", "events_produced", "events_consumed", "methods"
]

VALID_TIERS = ["tier_0_kernel", "tier_1_system", "tier_2_functional", "tier_3_tool"]

def main():
    errors = 0
    for skill_json in Path("skills").rglob("skill.json"):
        with open(skill_json) as f:
            data = json.load(f)
        for field in REQUIRED_FIELDS:
            if field not in data:
                print(f"Missing '{field}' in {skill_json}")
                errors += 1
        if data.get("tier") not in VALID_TIERS:
            print(f"Invalid tier '{data.get('tier')}' in {skill_json}")
            errors += 1
    sys.exit(errors)

if __name__ == "__main__":
    main()
```

---

## 十二、依赖管理

### 12.1 requirements.txt

```
psutil>=5.9.0
pyyaml>=6.0
pytest>=7.0
pytest-asyncio>=0.21
pre-commit>=3.0
```

### 12.2 安装

```bash
pip install -r requirements.txt
```

### 12.3 添加新依赖

- 添加前确认是否真的需要
- 锁定最低版本号
- 更新 requirements.txt
- 提交 `chore: 添加 xxx 依赖`

---

## 十三、验证命令

```bash
# 语法检查
python -m py_compile core/agent_loop.py

# 核心模块导入
python -c "from core.agent_loop import AgentLoop; print('OK')"

# 技能加载
python -c "from core.skill_registry import SkillRegistry; r = SkillRegistry(); r.scan(); print(f'{len(r.skills)} skills')"

# CLI 测试
python channels/cli.py --query "你好"

# 单元测试
pytest tests/ -v

# 覆盖率
pytest tests/ --cov=core --cov-report=term-missing

# Pre-commit 检查
pre-commit run --all-files
```

---

## 十四、Auto Commit 工具

创建 `tools/auto_commit.py`：

```python
import subprocess
from plector.core.function_calling import tool

@tool
def commit(message: str) -> dict:
    """
    自动提交 Git 变更

    参数:
        message: 提交信息

    返回:
        {"success": bool, "message": str}
    """
    try:
        subprocess.run(["git", "add", "."], check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True, text=True)
        subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
        return {"success": True, "message": f"已提交并推送：{message}"}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": e.stderr}
```

---

## 十五、.gitignore

```
# 运行时
logs/
data/
__pycache__/
*.pyc

# IDE
.vscode/
.idea/

# 环境
.env
venv/
.venv/

# OS
.DS_Store
Thumbs.db
```

---

## 参考资料

- [PEP 8](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [NanoBot](https://github.com/HKUDS/NanoBot)

---

*本规范会持续更新。*

```

---
