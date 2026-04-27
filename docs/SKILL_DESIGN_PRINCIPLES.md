# 技能设计规范

> 本文档定义了 Plector 技能的标准化设计原则，确保所有技能具有一致的可发现性和可用性。

## 1. 技能设计原则

### 1.1 完整性原则
每个 skill.json 必须包含以下字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 是 | 技能唯一标识，使用 snake_case |
| description | 是 | 完整的功能描述 |
| version | 是 | 语义版本号 (x.y.z) |
| tier | 是 | 层级：tier_1_system / tier_2_functional / tier_3_advanced |
| dependencies | 是 | 依赖的其他技能列表 |
| triggers | **是** | 触发词列表（用于自动路由） |
| events_produced | 是 | 该技能产生的事件 |
| events_consumed | 是 | 该技能消费的事件 |
| tools | 是 | 工具函数列表 |

### 1.2 触发词原则
触发词是 AI Agent 自动路由的关键，必须：
- 包含用户常用的自然语言表达
- 覆盖不同的使用场景
- 使用中文（因为用户偏好中文交流）

**触发词格式要求**：
```json
{
  "description": "技能描述...",
  "triggers": ["触发词1", "触发词2", "触发词3"]
}
```

### 1.3 描述质量原则
技能描述必须：
- 清晰说明功能范围
- 包含使用场景
- 说明返回值格式（如有）
- 提及依赖关系
- 如有必要，说明限制条件

**示例 - 好的描述**：
```json
{
  "description": "记忆管理技能，存储和查询对话历史、用户偏好、知识记忆。当用户提到"记住"、"回忆"、"偏好"、"之前聊过"时使用。返回格式：{success, data, error}。"
}
```

**示例 - 不好的描述**：
```json
{
  "description": "记忆管理技能"
}
```

### 1.4 工具函数原则
每个工具函数必须包含：
- name: 函数名（snake_case）
- description: 清晰的参数和返回值说明
- inputSchema: 完整的 JSON Schema 定义

**示例**：
```json
{
  "name": "save_conversation",
  "description": "保存对话记录到记忆数据库。参数：session_id(会话ID), role(角色), content(内容)。返回值：{success, data, error}",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "会话 ID"
      },
      "role": {
        "type": "string",
        "description": "角色（user 或 assistant）"
      },
      "content": {
        "type": "string",
        "description": "对话内容"
      }
    },
    "required": ["session_id", "role", "content"],
    "additionalProperties": false
  }
}
```

---

## 2. 标准 skill.json 模板

```json
{
  "name": "skill_name",
  "display_name": "显示名称",
  "description": "技能完整描述，包含功能范围、使用场景、返回值格式。",
  "version": "1.0.0",
  "tier": "tier_2_functional",
  "triggers": ["触发词1", "触发词2", "触发词3"],
  "category": "功能类别",
  "author": "Plector Team",
  "created": "2026-01-01",
  "tags": ["tag1", "tag2"],
  "dependencies": {
    "other_skill": "依赖说明"
  },
  "config": {
    "key": "value"
  },
  "events_produced": ["event.name"],
  "events_consumed": ["event.name"],
  "tools": [
    {
      "name": "tool_function",
      "description": "工具函数描述，说明参数和返回值。",
      "inputSchema": {
        "type": "object",
        "properties": {
          "param1": {
            "type": "string",
            "description": "参数1说明"
          }
        },
        "required": ["param1"],
        "additionalProperties": false
      }
    }
  ]
}
```

---

## 3. 触发词分类

### 系统级触发词 (tier_1)
| 技能 | 触发词 |
|------|--------|
| health_monitor | 系统健康、CPU、内存、磁盘状态、系统状态 |
| memory | 记住、回忆、偏好、之前聊过、知识、记得 |
| context_refresher | 上下文保鲜、GSD、长对话、防止遗忘 |

### 功能级触发词 (tier_2)
| 技能 | 触发词 |
|------|--------|
| code_writer | 写代码、创建文件、修改代码、新建代码 |
| file_utils | 文件操作、列出文件、移动文件、复制文件 |
| test_runner | 运行测试、执行测试、pytest |
| error_knowledge | 报错、出错了、遇到错误、错误分析 |
| web_search | 搜索、查找信息、网上搜索 |

### 高级触发词 (tier_3)
| 技能 | 触发词 |
|------|--------|
| agency_orchestrator | 工作流、多角色协作、DAG、执行流程 |
| auto_developer | 自动开发、一键开发、需求开发 |
| self_improver | 自我改进、升级、自优化 |

---

## 4. 层级定义

| 层级 | 说明 | 示例 |
|------|------|------|
| tier_1_system | 系统核心功能 | memory, health_monitor, context_refresher |
| tier_2_functional | 基础功能模块 | code_writer, file_utils, test_runner |
| tier_3_advanced | 高级功能 | agency_orchestrator, auto_developer, self_improver |

---

## 5. 事件系统

### 标准事件格式
```
{domain}.{action}
```

### 常用事件
| 事件 | 生产者 | 消费者 | 说明 |
|------|--------|--------|------|
| memory.stored | memory | - | 记忆已存储 |
| memory.retrieved | memory | - | 记忆已检索 |
| health.degraded | health_monitor | - | 健康状态降级 |
| test.passed | test_runner | error_knowledge | 测试通过 |
| test.failed | test_runner | error_knowledge | 测试失败 |
| workflow.executed | agency_orchestrator | - | 工作流已执行 |
| auto_develop.started | auto_developer | - | 自动开发启动 |
| code.written | code_writer | - | 代码已写入 |

---

## 6. 检查清单

创建新技能时，必须检查：

- [ ] name 唯一且使用 snake_case
- [ ] description 包含完整说明
- [ ] version 符合语义版本
- [ ] tier 正确分类
- [ ] triggers 包含至少 3 个触发词
- [ ] tools 每个函数有完整 inputSchema
- [ ] events_produced 定义清晰
- [ ] events_consumed 定义清晰
- [ ] dependencies 列出所有依赖
- [ ] 测试覆盖所有工具函数

---

## 7. 参考资料

- [技能目录](../skills/)
- [可发现性报告](./reports/skill_discoverability_report.md)
- [Plector 架构设计](../docs/specs/Design_Plector_v1.2.md)
