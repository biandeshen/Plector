# Context Refresher 技能规范

## 技能概述

**技能名称**: context_refresher  
**版本**: 1.1.0  
**层级**: tier_2_enhanced  
**功能**: GSD（Goal-State-Drift）上下文保鲜，防止长对话中 AI 遗忘初始目标

## 问题背景

在长对话（50+ 轮次）中，AI 模型容易"遗忘"用户的初始目标，导致：
- 偏离核心任务
- 重复询问已明确的信息
- 无法准确评估任务完成度

## 解决方案

### 核心机制

```
┌─────────────────────────────────────────────────────────────┐
│                    GSD 上下文保鲜流程                          │
├─────────────────────────────────────────────────────────────┤
│  1. 触发条件: 对话轮次 % 10 == 0                              │
│  2. LLM 提取: {goal, constraints, completed[], in_progress[]}│
│  3. 存储: vector_memory.context_saver collection             │
│  4. 注入: 新消息时拼接 {保鲜上下文 + 最近 5 轮}               │
│  5. 重锚定: 用户明确修改目标时触发                             │
└─────────────────────────────────────────────────────────────┘
```

### 数据结构

```json
{
  "goal": "用户初始目标（首条消息）",
  "constraints": ["约束条件1", "约束条件2"],
  "completed": ["已完成任务1", "已完成任务2"],
  "in_progress": ["进行中任务"],
  "turns": 15,
  "session_id": "xxx"
}
```

## 接口定义

### 1. preserve（保鲜）

**描述**: 触发上下文保鲜，从对话历史中提取并存储目标信息

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| conversation_history | array | 是 | 对话历史 [{"role": "user/assistant", "content": str}] |
| session_id | string | 否 | 会话 ID，默认 "default" |

**返回**:
```json
{
  "success": true,
  "data": {
    "goal": "目标内容",
    "turns_preserved": 15,
    "completed_count": 2,
    "in_progress_count": 1
  }
}
```

### 2. re_anchor（重锚定）

**描述**: 重锚定上下文，当用户明确修改目标时调用

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| new_goal | string | 是 | 新的目标 |
| new_constraints | array | 否 | 新的约束条件 |
| session_id | string | 否 | 会话 ID，默认 "default" |

**返回**:
```json
{
  "success": true,
  "data": {
    "goal": "新目标内容",
    "constraints": ["约束1"]
  }
}
```

### 3. get_context（获取上下文）

**描述**: 获取最新保鲜上下文

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 否 | 会话 ID，默认 "default" |

**返回**:
```json
{
  "success": true,
  "data": {
    "goal": "目标内容",
    "constraints": [],
    "completed": [],
    "in_progress": [],
    "turns": 15
  }
}
```

## 使用示例

### 基础用法

```python
from skills.context_refresher import SkillHandler

handler = SkillHandler()

# 保鲜
result = await handler.preserve(conversation_history)

# 重锚定（用户明确修改目标）
result = await handler.re_anchor(
    new_goal="新的目标",
    new_constraints=["约束1", "约束2"]
)

# 获取上下文
context = await handler.get_context()
```

### 在 Agent 循环中集成

```python
class AgentLoop:
    def __init__(self):
        self.context_refresher = SkillHandler()
        self.turn_count = 0

    async def process_message(self, message: str):
        # 添加到历史
        self.history.append({"role": "user", "content": message})
        self.turn_count += 1

        # 每 10 轮触发保鲜
        if self.turn_count % 10 == 0:
            await self.context_refresher.preserve(self.history)

        # 构建上下文
        context = await self.context_refresher.get_context()
        if context["success"]:
            injected = self.context_refresher.build_injected_context(
                context["data"], self.history[-5:]
            )
            # 注入到 prompt

        # 正常处理消息...
```

## 事件发布

技能会发布以下事件到 EventBus：

| 事件 | 载荷 |
|------|------|
| `context.preserved` | `{goal, constraints, completed, in_progress, turns, session_id}` |
| `context.re_anchored` | `{new_goal, constraints, session_id}` |

## 依赖

- `core.vector_memory.VectorMemory`
- `core.event_bus.EventBus`

## 实现文件

- `skills/context_refresher/implementation.py` - 技能实现
- `skills/context_refresher/skill.json` - 技能元数据
- `core/vector_memory.py` - 包含 context_saver collection

## 限制

- 目标字段最大 200 字符
- 最近轮次注入最多 5 轮
- 保鲜间隔 10 轮（可配置）

## 验收标准

- [ ] 长对话（50+ 轮）后 AI 仍能准确回答初始目标
- [ ] 保鲜事件正确发布到 EventBus
- [ ] 上下文正确存储到 vector_memory
- [ ] 重锚定能覆盖旧的上下文
- [ ] 单元测试覆盖核心方法
