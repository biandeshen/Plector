---
title: Technical Specification
category: standards
last_updated: 2026-04-04
version: 1.0.0
---

# Plector Technical Specification

*Version: 1.0.0*
*Updated: 2026-04-04*

> 本文档定义 Plector 所有技术接口的格式规范。
> 直接对齐业内标准，不发明私有格式。

---

## 对齐标准一览

| 组件 | 标准 | 说明 |
|------|------|------|
| 技能定义 | MCP Tool 格式 | `tools` + `inputSchema` |
| 工具 Schema | OpenAI Function Calling | `strict: true` + `additionalProperties: false` |
| 事件格式 | CloudEvents 1.0 | `specversion/id/source/type/time/data` |
| 错误格式 | JSON-RPC 2.0 | `jsonrpc/error.code/error.message` |
| 参数校验 | JSON Schema Draft 2020-12 | 完整 JSON Schema |
| 工具名称 | OpenAI 命名规范 | `{skill_name}_{method_name}`（`_` 分隔） |

---

## 一、Tool/Function Calling 格式（OpenAI）

### 1.1 Tool Schema

```json
{
  "type": "function",
  "function": {
    "name": "health_monitor_check_health",
    "description": "执行健康检查",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": [],
      "additionalProperties": false
    },
    "strict": true
  }
}
```

### 1.2 Tool Call（LLM 返回）

```json
{
  "id": "call_abc123",
  "type": "function",
  "function": {
    "name": "health_monitor_check_health",
    "arguments": "{}"
  }
}
```

### 1.3 Tool Result（返回给 LLM）

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "data": {"cpu": 12.5, "memory": 45.0, "disk": 30.0, "status": "healthy"},
    "error": null
  }
}
```

---

## 二、JSON Schema 规范

### 2.1 参数定义

```json
{
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
```

### 2.2 Python 类型映射

| Python | JSON Schema |
|--------|-------------|
| `str` | `{"type": "string"}` |
| `int` | `{"type": "integer"}` |
| `float` | `{"type": "number"}` |
| `bool` | `{"type": "boolean"}` |
| `list` | `{"type": "array", "items": {}}` |
| `dict` | `{"type": "object", "properties": {}}` |

---

## 三、skill.json 格式（MCP Tool）

```json
{
  "name": "health_monitor",
  "description": "获取系统健康状态",
  "version": "1.0.0",
  "tier": "tier_1_system",
  "dependencies": [],
  "events_produced": ["health.degraded"],
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

---

## 四、事件格式（CloudEvents 1.0）

```json
{
  "specversion": "1.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "health_monitor",
  "type": "health.degraded",
  "time": "2026-04-04T10:00:00Z",
  "data": {
    "cpu": 85.0,
    "memory": 90.0,
    "disk": 45.0
  }
}
```

---

## 五、错误格式（JSON-RPC 2.0）

### 5.1 成功

```json
{
  "jsonrpc": "2.0",
  "result": {"success": true, "data": {...}, "error": null}
}
```

### 5.2 失败

```json
{
  "jsonrpc": "2.0",
  "error": {"code": -32601, "message": "工具 health_monitor_xxx 不存在"}
}
```

### 5.3 错误码

| code | 含义 | 触发条件 |
|------|------|---------|
| -32700 | Parse error | JSON 解析失败 |
| -32600 | Invalid Request | 请求格式错误 |
| -32601 | Method not found | 工具/方法不存在 |
| -32602 | Invalid params | 参数错误 |
| -32603 | Internal error | 执行异常 |

---

## 六、配置格式

### 6.1 环境变量语法

| 语法 | 说明 |
|------|------|
| `${VAR}` | 必需，不存在则报错 |
| `${VAR:-default}` | 可选，不存在则用默认值 |

### 6.2 closed_loops.yaml

```yaml
loop_id:
  trigger_on: ["event.type"]
  entry: "first_node"
  max_iterations: 5
  nodes:
    first_node:
      type: "skill"
      skill: "skill_name"
      method: "method_name"
      next: "second_node"
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

---

## 参考资料

- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [CloudEvents](https://cloudevents.io/)
- [JSON-RPC 2.0](https://www.jsonrpc.org/specification)
- [JSON Schema](https://json-schema.org/)
