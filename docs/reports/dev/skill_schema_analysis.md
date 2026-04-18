# Skill Schema 一致性分析报告

> **重要更正 (2026-04-18)**
> 本报告之前版本存在错误。正确的标准应以 `SKILL_DESIGN_PRINCIPLES.md` 为准。
> 以下为修正后的报告。

生成时间: 2026-04-18

## 概述

对 `skills/` 目录下技能的 `skill.json` 进行分析，基于 `SKILL_DESIGN_PRINCIPLES.md` 定义的标准。

## SKILL_DESIGN_PRINCIPLES.md 定义的标准字段

根据设计文档 Section 1.1，以下字段为标准必填字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `name` | 是 | string | 技能唯一标识，使用 snake_case |
| `description` | 是 | string | 完整的功能描述 |
| `version` | 是 | string | 语义版本号 (x.y.z) |
| `tier` | 是 | string | 层级：tier_1_system / tier_2_functional / tier_3_advanced |
| `dependencies` | 是 | **array 或 object** | 依赖的其他技能列表 |
| `triggers` | **是** | **array 或 object** | 触发词列表 |
| `events_produced` | 是 | array | 产出事件列表 |
| `events_consumed` | 是 | array | 消费事件列表 |
| `tools` | 是 | array | 工具函数列表 |

设计文档模板还包含以下可选字段：`display_name`, `category`, `author`, `created`, `tags`, `config`, `data_structures`

## 实际问题

### self_improver 缺少 required 字段

`start_upgrade`、`get_status`、`stop_upgrade` 三个工具的 inputSchema 缺少 `required` 字段。

```json
// get_status 和 stop_upgrade 需要添加：
"inputSchema": {
  "type": "object",
  "properties": {},
  "required": [],  // 缺少这个字段
  "additionalProperties": false
}
```

## 验证脚本输出

```
[skills\self_improver\skill.json] Missing inputSchema field 'required' in tool 'start_upgrade'
[skills\self_improver\skill.json] Missing inputSchema field 'required' in tool 'get_status'
[skills\self_improver\skill.json] Missing inputSchema field 'required' in tool 'stop_upgrade'
```

## 修复记录

### 2026-04-18 修复

- [x] self_improver: 为 `get_status` 和 `stop_upgrade` 添加 `"required": []`
- [x] 回滚错误修改：恢复了 context_refresher、error_knowledge 中被错误移除的标准字段

## 符合标准的技能

以下技能的 schema 完全符合标准：

- [x] health_monitor
- [x] code_writer
- [x] file_utils
- [x] test_runner
- [x] web_search
- [x] memory
- [x] agency_orchestrator
- [x] auto_developer
- [x] context_refresher (恢复后)
- [x] error_knowledge (恢复后)
- [x] self_improver (修复后)

## 字段类型说明

### dependencies 字段

设计文档模板显示 `dependencies` 可以是：
- **object** (带说明): `{"skill_name": "说明"}`
- **array**: `["skill_name"]`

两者都是合法的。

### triggers 字段

triggers 是**必填字段**，可以是：
- **array**: `["触发词1", "触发词2"]`
- **object** (带说明): `{"key": "说明"}`

两者都是合法的。
