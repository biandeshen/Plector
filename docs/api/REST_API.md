# REST API Reference

Plector WebSocket 渠道提供 REST API 用于查询系统状态、技能、工具、对话历史等。

**Base URL:** `http://localhost:8080`

---

## GET /api/health

系统健康状态

### Response

```json
{
  "cpu": 25.5,
  "memory": 60.2,
  "memory_total": 32.0,
  "memory_used": 19.3,
  "disk": 45.0,
  "disk_total": 512.0,
  "disk_used": 230.4,
  "status": "healthy"
}
```

| Field | Type | Description |
|-------|------|-------------|
| cpu | number | CPU 使用率 (%) |
| memory | number | 内存使用率 (%) |
| memory_total | number | 总内存 (GB) |
| memory_used | number | 已用内存 (GB) |
| disk | number | 磁盘使用率 (%) |
| disk_total | number | 总磁盘空间 (GB) |
| disk_used | number | 已用磁盘空间 (GB) |
| status | string | `healthy` 或 `degraded` |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功返回健康状态 |

---

## GET /api/skills

技能列表

### Response

```json
{
  "skills": [
    {
      "name": "health_monitor",
      "description": "系统健康监控技能",
      "version": "1.0.0",
      "tier": "core",
      "tools": [
        {
          "name": "health_monitor_get_status",
          "description": "获取系统健康状态"
        }
      ]
    }
  ],
  "total": 5
}
```

| Field | Type | Description |
|-------|------|-------------|
| skills | array | 技能列表 |
| skills[].name | string | 技能名称 |
| skills[].description | string | 技能描述 |
| skills[].version | string | 技能版本 |
| skills[].tier | string | 技能层级 (core/extended) |
| skills[].tools | array | 技能提供的工具列表 |
| total | number | 技能总数 |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功返回技能列表 |

---

## GET /api/tools

工具列表 (本地工具 + MCP 工具)

### Response

```json
{
  "local": [
    {
      "name": "filesystem_read",
      "description": "读取文件内容"
    }
  ],
  "mcp": [
    {
      "name": "mcp_filesystem_server_read",
      "description": "MCP 文件系统服务器读取"
    }
  ],
  "total": 12
}
```

| Field | Type | Description |
|-------|------|-------------|
| local | array | 本地工具列表 |
| mcp | array | MCP 工具列表 |
| total | number | 工具总数 |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功返回工具列表 |

---

## GET /api/events

事件日志

### Response

```json
{
  "events": [
    {
      "time": "2026-04-18T10:30:00.123456",
      "type": "ws.message",
      "data": {
        "role": "user",
        "content": "你好"
      }
    }
  ],
  "total": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| events | array | 事件列表 (最近 100 条) |
| events[].time | string | ISO 格式时间戳 |
| events[].type | string | 事件类型 |
| events[].data | object | 事件数据 |
| total | number | 事件总数 |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功返回事件日志 |

---

## GET /api/conversations

对话历史列表

### Response

```json
{
  "conversations": [
    {
      "session_id": "abc123def456",
      "title": "帮我分析代码..."
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| conversations | array | 对话列表 (最近 50 条) |
| conversations[].session_id | string | 会话 ID |
| conversations[].title | string | 对话标题 (最多 30 字符) |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功返回对话列表 |

---

## GET /api/conversations/{session_id}

获取指定对话的消息

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | string | Yes | 会话 ID |

### Response

```json
{
  "session_id": "abc123def456",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "你好，请帮我分析这段代码"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "好的，我来帮你分析..."
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | 会话 ID |
| messages | array | 消息列表 |
| messages[].id | number | 消息 ID (rowid) |
| messages[].role | string | 角色 (user/assistant) |
| messages[].content | string | 消息内容 |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功返回对话消息 |
| 500 | 获取对话失败 |

### Example

```bash
curl http://localhost:8080/api/conversations/abc123def456
```

---

## POST /api/conversations

创建新对话

### Request Body

无 (空请求体)

### Response

```json
{
  "session_id": "abc123def456",
  "message": "新对话已创建"
}
```

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | 新创建的会话 ID |
| message | string | 创建结果消息 |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功创建对话 |

### Example

```bash
curl -X POST http://localhost:8080/api/conversations
```

---

## PATCH /api/conversations/{session_id}

重命名对话

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | string | Yes | 会话 ID |

### Request Body

```json
{
  "title": "新标题"
}
```

| Field | Type | Required | Description |
|-----------|------|----------|-------------|
| title | string | Yes | 新标题 (不能为空) |

### Response

```json
{
  "session_id": "abc123def456",
  "title": "新标题"
}
```

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | 会话 ID |
| title | string | 更新后的标题 |

### Error Response

```json
{
  "error": "标题不能为空"
}
```

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功重命名对话 |
| 500 | 重命名失败 |

### Example

```bash
curl -X PATCH http://localhost:8080/api/conversations/abc123def456 \
  -H "Content-Type: application/json" \
  -d '{"title": "代码分析"}'
```

---

## DELETE /api/conversations/{session_id}

删除对话

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | string | Yes | 会话 ID |

### Response

```json
{
  "deleted": 10,
  "session_id": "abc123def456"
}
```

| Field | Type | Description |
|-------|------|-------------|
| deleted | number | 删除的消息数量 |
| session_id | string | 被删除的会话 ID |

### Error Response

```json
{
  "error": "错误信息"
}
```

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功删除对话 |
| 500 | 删除失败 |

### Example

```bash
curl -X DELETE http://localhost:8080/api/conversations/abc123def456
```

---

## GET /api/config

当前配置

### Response

```json
{
  "llm_provider": "ollama",
  "max_iterations": 10,
  "skills_count": 5,
  "tools_count": 12
}
```

| Field | Type | Description |
|-------|------|-------------|
| llm_provider | string | LLM 提供商 |
| max_iterations | number | 最大迭代次数 |
| skills_count | number | 已注册技能数量 |
| tools_count | number | 已注册工具数量 |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功返回配置 |

---

## GET /api/metrics

Prometheus 指标

### Response

```json
{
  "requests_total": 150,
  "requests_success": 145,
  "requests_failed": 5,
  "websocket_connections_active": 3,
  "websocket_connections_total": 50,
  "response_time_avg": 0.25,
  "response_time_p95": 1.2,
  "tokens_used": 50000
}
```

| Field | Type | Description |
|-------|------|-------------|
| requests_total | number | 总请求数 |
| requests_success | number | 成功请求数 |
| requests_failed | number | 失败请求数 |
| websocket_connections_active | number | 当前活跃 WebSocket 连接数 |
| websocket_connections_total | number | 历史 WebSocket 连接总数 |
| response_time_avg | number | 平均响应时间 (秒) |
| response_time_p95 | number | P95 响应时间 (秒) |
| tokens_used | number | 已使用 tokens 总数 |

### Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功返回指标 |

---

## Error Responses

所有 API 端点可能返回以下错误格式：

```json
{
  "error": "错误描述"
}
```

| Status Code | Description |
|-------------|-------------|
| 500 | 服务器内部错误 |
