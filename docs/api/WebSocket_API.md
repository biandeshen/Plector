# WebSocket API Reference

Plector WebSocket 渠道提供实时对话功能，支持流式响应和工具执行状态推送。

**Endpoint:** `ws://localhost:8080/ws`

---

## Connection

### Establish Connection

```javascript
const ws = new WebSocket("ws://localhost:8080/ws");

ws.onopen = () => {
  console.log("Connected to Plector");
};
```

### Reconnection Strategy

推荐的重连策略：

```javascript
class PlectorReconnector {
  constructor(url, options = {}) {
    this.url = url;
    this.maxRetries = options.maxRetries || 5;
    this.retryDelay = options.retryDelay || 1000;
    this.onMessage = options.onMessage || (() => {});
    this.onError = options.onError || (() => {});
    this.ws = null;
    this.retryCount = 0;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log("Connected");
      this.retryCount = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.onMessage(message);
    };

    this.ws.onerror = (error) => {
      this.onError(error);
    };

    this.ws.onclose = () => {
      if (this.retryCount < this.maxRetries) {
        this.retryCount++;
        const delay = this.retryDelay * Math.pow(2, this.retryCount - 1);
        console.log(`Reconnecting in ${delay}ms... (${this.retryCount}/${this.maxRetries})`);
        setTimeout(() => this.connect(), delay);
      } else {
        console.error("Max retries reached");
      }
    };
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error("WebSocket not connected");
    }
  }
}
```

### Exponential Backoff

重连延迟建议使用指数退避：
- 第 1 次重连: 1s
- 第 2 次重连: 2s
- 第 3 次重连: 4s
- 第 4 次重连: 8s
- 第 5 次重连: 16s

---

## Message Format

所有消息均为 JSON 格式。

### Client to Server

```json
{
  "content": "用户输入文本",
  "session_id": "可选的会话ID"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | string | Yes | 用户输入文本 |
| session_id | string | No | 指定会话 ID，用于继续对话 |

### Server to Client

```json
{
  "type": "消息类型",
  "content": "消息内容",
  ...其他字段
}
```

---

## Event Types

### thinking

AI 正在思考

```json
{
  "type": "thinking",
  "content": "思考中..."
}
```

### chunk

流式响应片段

```json
{
  "type": "chunk",
  "content": "部分响应内容"
}
```

**说明:** 多个 `chunk` 消息组合起来构成完整的响应内容。

### toolExecuting

工具开始执行

```json
{
  "type": "toolExecuting",
  "tool": "filesystem_read"
}
```

| Field | Type | Description |
|-------|------|-------------|
| tool | string | 正在执行的工具名称 |

### toolDone

工具执行完成

```json
{
  "type": "toolDone",
  "tool": "filesystem_read"
}
```

| Field | Type | Description |
|-------|------|-------------|
| tool | string | 已完成的工具名称 |

### tool_call_start

工具调用开始通知

```json
{
  "type": "tool_call_start",
  "count": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| count | number | 将要执行的工具数量 |

### response

完整响应 (done 事件后发送)

```json
{
  "type": "response",
  "content": "这是完整的AI响应内容"
}
```

**说明:** 当 `done` 事件收到后，`response` 消息包含过滤后的完整响应内容（已移除 think 标签）。

### done

流式响应结束

```json
{
  "type": "done",
  "content": "完整响应内容（包含think标签）"
}
```

**说明:** 这是流式响应的结束信号，`content` 字段包含原始内容（可能有 think 标签）。

### error

错误消息

```json
{
  "type": "error",
  "content": "执行失败: 错误描述"
}
```

---

## Message Flow Example

### 完整对话流程

```
Client -> Server: {"content": "帮我分析这段代码", "session_id": "abc123"}
Server -> Client: {"type": "thinking", "content": "思考中..."}
Server -> Client: {"type": "tool_call_start", "count": 2}
Server -> Client: {"type": "toolExecuting", "tool": "filesystem_read"}
Server -> Client: {"type": "toolDone", "tool": "filesystem_read"}
Server -> Client: {"type": "chunk", "content": "我来帮你分析..."}
Server -> Client: {"type": "toolExecuting", "tool": "code_analyzer"}
Server -> Client: {"type": "toolDone", "tool": "code_analyzer"}
Server -> Client: {"type": "chunk", "content": "这段代码的问题在于..."}
Server -> Client: {"type": "done", "content": "<think>分析中...</think>这段代码的问题在于..."}
Server -> Client: {"type": "response", "content": "这段代码的问题在于..."}
```

### 简单响应流程

```
Client -> Server: {"content": "你好"}
Server -> Client: {"type": "thinking", "content": "思考中..."}
Server -> Client: {"type": "chunk", "content": "你好！"}
Server -> Client: {"type": "chunk", "content": "有什么可以帮助你的吗？"}
Server -> Client: {"type": "done", "content": "你好！有什么可以帮助你的吗？"}
Server -> Client: {"type": "response", "content": "你好！有什么可以帮助你的吗？"}
```

---

## Rate Limiting

服务端实施速率限制，按 IP 地址限制请求频率。

如果请求过于频繁，会返回：

```json
{
  "type": "error",
  "content": "请求过于频繁，请稍后再试"
}
```

---

## Session Management

### 创建新对话

不提供 `session_id`，系统会创建新的会话：

```javascript
ws.send(JSON.stringify({
  content: "开始新对话"
}));
```

返回的 `session_id` 可用于后续消息。

### 继续对话

提供 `session_id` 以继续特定对话：

```javascript
ws.send(JSON.stringify({
  content: "继续之前的话题",
  "session_id": "abc123def456"
}));
```

### 自动标题生成

首次对话时，系统会自动从用户消息中提取关键词生成会话标题。

---

## JavaScript Client Example

```javascript
class PlectorClient {
  constructor(url = "ws://localhost:8080/ws") {
    this.url = url;
    this.ws = null;
    this.sessionId = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("Connected to Plector");
        resolve();
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        reject(error);
      };
    });
  }

  send(content, sessionId = null) {
    return new Promise((resolve, reject) => {
      const message = { content };
      if (sessionId) {
        message.session_id = sessionId;
      }

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "response") {
          resolve({
            type: msg.type,
            content: msg.content,
            sessionId: this.sessionId
          });
        } else if (msg.type === "error") {
          reject(new Error(msg.content));
        }
      };

      this.ws.send(JSON.stringify(message));
    });
  }

  onChunk(callback) {
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "chunk") {
        callback(msg.content);
      }
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const client = new PlectorClient();
await client.connect();

// Stream chunks
client.onChunk((chunk) => {
  process.stdout.write(chunk);
});

// Send message
const response = await client.send("帮我分析这段代码");
console.log("\nFull response:", response.content);
```

---

## Error Codes

| Error | Description |
|-------|-------------|
| 请求过于频繁 | 速率限制触发 |
| 执行失败: ... | Agent 执行出错 |
| WebSocket disconnected | 连接已关闭 |
