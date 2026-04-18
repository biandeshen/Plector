# Skill Schema 一致性分析报告

生成时间: 2026-04-18

## 概述

对 `skills/` 目录下 11 个技能的 `skill.json` 进行分析，发现存在多处 schema 不一致问题。

## 验证脚本输出

```
[skills\self_improver\skill.json] Missing inputSchema field 'required' in tool 'start_upgrade'
[skills\self_improver\skill.json] Missing inputSchema field 'required' in tool 'get_status'
[skills\self_improver\skill.json] Missing inputSchema field 'required' in tool 'stop_upgrade'
```

## 标准 Schema 字段

以下字段应为所有 skill.json 的标准字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 技能名称（小写、下划线分隔） |
| `description` | string | 技能描述 |
| `version` | string | 版本号（语义化版本） |
| `tier` | string | 层级（tier_1_system / tier_2_functional / tier_3_advanced） |
| `dependencies` | array | 依赖技能列表 |
| `events_produced` | array | 产出事件列表 |
| `events_consumed` | array | 消费事件列表 |
| `tools` | array | 工具列表 |

## 不一致字段汇总

### 1. context_refresher (问题最多)

| 字段 | 当前类型 | 问题 | 建议 |
|------|----------|------|------|
| `dependencies` | **object** | 违反标准，应为 array | 改为 `[]` 或移除 |
| `display_name` | string | 非标准字段 | 移除或移至 description |
| `category` | string | 非标准字段 | 移除 |
| `author` | string | 非标准字段 | 移除 |
| `created` | string | 非标准字段 | 移除 |
| `tags` | array | 非标准字段 | 移除 |
| `config` | object | 非标准字段 | 移除（配置应放单独文件） |
| `triggers` | **object** | 类型不一致（其他为 array） | 移除或改为 array |
| `data_structures` | object | 非标准字段 | 移除 |

### 2. error_knowledge

| 字段 | 当前类型 | 问题 | 建议 |
|------|----------|------|------|
| `display_name` | string | 非标准字段 | 移除或移至 description |
| `category` | string | 非标准字段 | 移除 |
| `triggers` | array | 非标准字段（但类型正确） | 移除 |

### 3. self_improver

| 字段 | 当前类型 | 问题 | 建议 |
|------|----------|------|------|
| `display_name` | string | 非标准字段 | 移除或移至 description |
| `category` | string | 非标准字段 | 移除 |
| `triggers` | array | 非标准字段 | 移除 |

### 4. auto_developer

无明显不一致，schema 基本标准。

## 关键问题

### 问题 1: dependencies 类型不一致

- **context_refresher**: `dependencies` 是 object
  ```json
  "dependencies": {
    "core/vector_memory.py": "双 collection 逻辑支持"
  }
  ```

- **其他技能**: `dependencies` 是 array
  ```json
  "dependencies": []
  "dependencies": ["agency_orchestrator"]
  ```

**影响**: 代码加载时需要判断类型，降低可靠性。

### 问题 2: self_improver 缺少 required 字段

三个工具 `start_upgrade`、`get_status`、`stop_upgrade` 的 inputSchema 缺少 `required` 数组。

### 问题 3: triggers 类型不一致

- `context_refresher`: `triggers` 是 **object**
- `error_knowledge` / `self_improver`: `triggers` 是 **array**

### 问题 4: 多个技能存在非标准字段

`display_name`、`category`、`author`、`created`、`tags`、`config`、`data_structures`、`triggers` 均非标准字段。

## 修复建议

### 立即修复 (Breaking)

1. **context_refresher**: 将 `dependencies` 从 object 改为 array
2. **self_improver**: 为三个工具添加 `required: []`

### 标准化 (非 Breaking)

制定标准 schema 后，逐步移除非标准字段：

| 字段 | 决策 |
|------|------|
| `display_name` | 移除，内容合并到 `description` |
| `category` | 移除，不应在 skill.json 中分类 |
| `author` | 移除，版本控制应使用 git |
| `created` | 移除，时间戳无实际意义 |
| `tags` | 移除，搜索功能不应依赖 skill.json |
| `config` | 移除，配置应放单独文件 |
| `triggers` | 移除，触发词匹配应在代码逻辑中 |
| `data_structures` | 移除，不应在配置中定义数据结构 |

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

## 待修复技能

- [ ] context_refresher (8 个问题)
- [ ] error_knowledge (3 个问题)
- [ ] self_improver (4 个问题 + 3 个 required 缺失)
