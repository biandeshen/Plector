# SKILL.md 技能格式规范深度研究

> 来源：agentskills.io 官方规范 + Medium
> 研究日期：2026-04-19

---

## 一、官方规范概述

### 1.1 规范来源

**SKILL.md** 是一个开放标准，由 agentskills.io 维护，旨在为 AI Agent 提供统一的技能描述格式。该标准已被多个项目采用，包括：
- Hermes Agent
- DeerFlow
- OpenClaw
- Claude Code

### 1.2 核心价值

| 价值 | 说明 |
|------|------|
| **可发现性** | 标准格式便于 Agent 自动发现和加载技能 |
| **可复用性** | 一次编写，可被多个 Agent 框架使用 |
| **可组合性** | 技能可嵌套组合形成复杂能力 |
| **可验证性** | 结构化格式便于验证完整性 |

---

## 二、SKILL.md 标准格式

### 2.1 必需字段

```markdown
# Skill Name                    # 必须：技能名称

## Description                 # 必须：简短描述
Brief description of what this skill does.

## Triggers                     # 必须：触发词列表
- trigger phrase 1
- trigger phrase 2
- trigger phrase 3

## Actions                      # 必须：动作定义
### Action 1
Step-by-step instructions for this action.

### Action 2
More detailed instructions.
```

### 2.2 可选字段

```markdown
## Examples                    # 示例
User: example trigger
Assistant: expected response

## Constraints                 # 约束条件
- Things the agent should not do
- Limitations or boundaries

## Dependencies                # 依赖关系
- skill_name: Description of dependency

## Configuration               # 配置选项
config_option: Description
default_value: "value"

## Notes                       # 注意事项
Additional context, tips, or caveats.

## Metadata                    # 元数据
version: 1.0.0
author: Author Name
tags: [tag1, tag2, tag3]
```

---

## 三、各项目实现对比

### 3.1 Hermes Agent 实现

```markdown
# Hermes Skill Format

## Description
Skill description here.

## Triggers
- trigger phrases

## Actions
### Main Action
Action details.

## Examples
Example conversations.

## Metadata
- name: skill_name
- version: 1.0.0
```

**特点：**
- 简化版格式
- Metadata 使用 YAML 风格
- 支持内置和可选技能分类

### 3.2 DeerFlow 实现

```markdown
# DeerFlow Skill

## Overview
Brief description.

## When to Use
Triggers and use cases.

## How It Works
Detailed action steps.

## Examples
Usage examples.

## Tips
Best practices.
```

**特点：**
- 按工作流组织
- 强调"何时使用"
- 包含实践技巧

### 3.3 OpenClaw 实现

```markdown
# OpenClaw Skill

## Description
Skill description.

## Triggers
- phrase 1
- phrase 2

## Actions
### Action Name
Steps for the action.

## Examples
Example 1...
Example 2...

## Notes
Additional info.
```

**特点：**
- 最简化格式
- 放在 `~/.openclaw/skills/<skill>/SKILL.md`
- 支持工作区共享

### 3.4 格式对比表

| 字段 | agentskills.io | Hermes | DeerFlow | OpenClaw |
|------|---------------|--------|----------|----------|
| Description | ✓ | ✓ | ✓ | ✓ |
| Triggers | ✓ | ✓ | ✓ | ✓ |
| Actions | ✓ | ✓ | ✓ | ✓ |
| Examples | ✓ | ✓ | ✓ | ✓ |
| Constraints | ✓ | ✗ | ✗ | ✗ |
| Dependencies | ✓ | ✗ | ✗ | ✗ |
| Configuration | ✓ | ✗ | ✗ | ✗ |
| Metadata | ✓ | ✓ | ✗ | ✗ |
| Notes | ✓ | ✓ | ✓ | ✓ |

---

## 四、SKILL.md 编写最佳实践

### 4.1 触发词设计

```markdown
## Triggers
# 好的触发词示例
- "帮我写代码"
- "生成测试用例"
- "review code"
- "analyze this function"

# 需要避免的触发词
- "help"        # 太模糊
- "do something" # 无意义
- "run"         # 需要上下文
```

**最佳实践：**
1. 使用具体、描述性的短语
2. 包含中英文触发词（国际化）
3. 按优先级排序（最常用在前）
4. 避免歧义词

### 4.2 动作定义

```markdown
## Actions
### primary_action
# 描述
清晰说明这个动作做什么。

# 步骤
1. First step
2. Second step
3. Third step

# 输出
描述期望的输出格式。

### secondary_action
# 描述
次要动作的说明。
```

**最佳实践：**
1. 使用分级标题（###）区分不同动作
2. 每个动作包含：描述、步骤、输出格式
3. 关键步骤用编号清晰列出
4. 提供错误处理说明

### 4.3 示例编写

```markdown
## Examples

### Example 1: Basic Usage
User: 生成一个冒泡排序函数
Assistant: 我将为您生成冒泡排序函数...

### Example 2: With Constraints
User: 用 Python 写一个排序算法，要求 O(n) 时间复杂度
Assistant: 根据您要求的 O(n) 复杂度，我推荐...

### Example 3: Error Handling
User: 读取不存在的文件
Assistant: 文件不存在。让我检查...
```

### 4.4 元数据规范

```markdown
## Metadata
version: 1.0.0
author: Plector Team
created: 2026-04-19
updated: 2026-04-19
tier: tier_2_functional
tags:
  - code-generation
  - python
  - algorithms
dependencies:
  - file_utils
conflicts:
  - deprecated_skill
```

---

## 五、Plector SKILL.md 格式设计

### 5.1 推荐的 Plector 格式

```markdown
# code_writer

## Metadata
```yaml
name: code_writer
version: 1.0.0
tier: tier_2_functional
author: Plector Team
created: 2026-04-15
```

## Description
代码编写技能，支持写入、读取、修改代码文件。支持多种编程语言，自动创建目录结构。

## Triggers
- "帮我写代码"
- "create a new file"
- "write function"
- "生成代码"
- "write test"

## Actions

### write_code
创建或覆盖代码文件。

**参数：**
- `filepath`: 文件路径（如 `src/main.py`）
- `code`: 代码内容

**输出：** 创建成功/失败状态

### read_code
读取代码文件内容。

**参数：**
- `filepath`: 文件路径

**输出：** 文件内容

### modify_code
修改现有文件中的代码片段。

**参数：**
- `filepath`: 文件路径
- `old_text`: 要替换的原文（精确匹配）
- `new_text`: 替换后的新内容

**输出：** 修改成功/失败状态

## Examples

### 创建新文件
User: 帮我创建一个 Python Web 服务器
Assistant: 我将为您创建一个简单的 Flask Web 服务器...

### 读取文件
User: 看看 src/app.py 的内容
Assistant: 以下是 `src/app.py` 的内容...

### 修改代码
User: 把 `hello` 改成 `world`
Assistant: 我将把 `src/app.py` 中的 `hello` 替换为 `world`...

## Constraints
- 不修改系统关键文件
- 备份重要文件后再修改
- 遵循项目代码规范

## Dependencies
- file_utils (用于目录创建)

## Notes
- 自动检测编程语言
- 支持代码格式化
- 保持原有缩进风格
```

---

## 六、SKILL.md 验证工具

### 6.1 验证脚本

```python
# scripts/validate_skill.py
import re
from pathlib import Path

def validate_skill_md(skill_path: Path) -> dict:
    """验证 SKILL.md 格式"""

    content = skill_path.read_text()
    errors = []
    warnings = []

    # 检查必需字段
    required_fields = ['Description', 'Triggers', 'Actions']
    for field in required_fields:
        if f'## {field}' not in content:
            errors.append(f"Missing required field: {field}")

    # 检查触发词格式
    if '## Triggers' in content:
        triggers_section = re.search(
            r'## Triggers\n(.*?)(?:\n##|\Z)',
            content,
            re.DOTALL
        )
        if triggers_section:
            triggers = re.findall(r'- (.+)', triggers_section.group(1))
            if len(triggers) < 1:
                warnings.append("Triggers section is empty")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
```

### 6.2 自动生成工具

```python
# scripts/generate_skill.py
def generate_skill_template(name: str, tier: str = "tier_2") -> str:
    """生成 SKILL.md 模板"""

    return f"""# {name}

## Metadata
```yaml
name: {name}
version: 1.0.0
tier: {tier}
author: Plector Team
created: {datetime.now().date()}
```

## Description
Brief description of the {name} skill.

## Triggers
- "触发词1"
- "触发词2"
- "trigger phrase 1"

## Actions

### primary_action
**描述：** 主要动作说明。

**参数：**
- `param1`: 参数说明
- `param2`: 参数说明

**输出：** 期望输出。

## Examples

### Basic Usage
User: 示例触发
Assistant: 期望响应...

## Constraints
- 约束条件 1
- 约束条件 2

## Dependencies
- dependency_skill: 依赖说明

## Notes
- 注意事项
- 最佳实践
```

---

## 七、参考资源

- [agentskills.io 官方规范](https://agentskills.io/specification)
- [SKILL.md Pattern 文章](https://bibek-poudel.medium.com/the-skill-md-pattern-how-to-write-ai-agent-skills-that-actually-work-72a3169dd7ee)
- [Hermes Agent 技能文档](https://hermes-agent.nousresearch.com/docs/skills/)

#SKILL.md #技能格式 #agentskills #标准化
