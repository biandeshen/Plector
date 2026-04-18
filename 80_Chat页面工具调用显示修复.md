---
tags:
  - v2.x
  - chat
  - bug-fix
  - websocket
  - frontend
type: bug-fix
created: 2026-04-18
related-to:
  - [[79_v2.x_流式响应-工具可视化实现方案]]
  - [[23_v1.2_WebSocket_Dashboard实现]]
  - [[81_Plector未来升级改造方案分析]]
---

> 日期: 2026-04-18
> 版本: v2.x
> 状态: 已完成

---

## 问题概述

Chat 页面存在 4 个交互问题：

| # | 问题 | 优先级 |
|---|------|--------|
| 1 | 工具调用刷新页面后不展示 | P0 |
| 2 | 回复后会在历史对话列表中出现空对话 | P1 |
| 3 | 回复的消息内容存在重复 | P1 |
| 4 | 工具调用和过程信息拼接在最终回复里 | P1 |

---

## 问题1: 工具调用刷新后不展示

### 根因分析

`websocket.py` 在处理 `toolDone` 事件时，只向 WebSocket 发送了事件，但没有将工具调用记录保存到数据库的 `tool_calls` 表。

前端切换到历史对话时，会调用 `/api/tool-calls/{session_id}` 获取工具调用记录。由于数据库中没有记录，所以工具调用信息丢失。

### 修复方案

在 `channels/websocket.py` 中添加 `_save_tool_call()` 函数，在处理 `toolDone` 事件时自动保存到数据库。

#### 1. 添加辅助函数

```python
# 消息索引计数器（每个 session）
_session_msg_index: dict[str, int] = {}


def _get_next_msg_index(session_id: str) -> int:
    """获取下一个消息索引"""
    if session_id not in _session_msg_index:
        _session_msg_index[session_id] = 0
    _session_msg_index[session_id] += 1
    return _session_msg_index[session_id]


def _save_tool_call(
    session_id: str,
    message_index: int,
    tool_name: str,
    arguments: str,
    result: str,
    elapsed: float,
):
    """保存工具调用记录到数据库"""
    try:
        import sqlite3

        conn = sqlite3.connect("data/plector.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tool_calls (session_id, message_index, tool_name, arguments, result, elapsed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, message_index, tool_name, arguments, result, elapsed),
        )
        conn.commit()
        conn.close()
        logger.debug(f"工具调用已保存: {tool_name} (session={session_id})")
    except Exception as e:
        logger.warning(f"保存工具调用失败: {e}")
```

#### 2. 修改事件处理逻辑

在 `_ws_process_stream_event()` 函数的 `toolDone` 分支中调用保存函数：

```python
elif t == "toolDone":
    tool_name = event.get("tool", "")
    tool_result = event.get("result", "") or event.get("error", "")
    tool_args = event.get("arguments", "")
    tool_elapsed = event.get("elapsed", 0.0)

    # 保存工具调用到数据库
    if session_id:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            _save_tool_call,
            session_id,
            _get_next_msg_index(session_id),
            tool_name,
            tool_args,
            str(tool_result)[:2000],  # 限制结果长度
            tool_elapsed,
        )

    await websocket.send_json({
        "type": "toolDone",
        "tool": tool_name,
        "toolId": event.get("toolId", ""),
        "result": tool_result,
        "error": event.get("error", ""),
    })
```

---

## 问题2: 空对话出现

### 根因分析

`finalize()` 函数在每次回复完成后都会调用 `addConversation()` 添加对话到前端列表：

```javascript
// 原代码
function finalize() {
    // ...
    if (buffer && buffer.length > 0) {
        addConversation(buffer.substring(0, 40));  // 问题在这里
    }
}
```

这导致：
1. 对话是添加到前端本地列表，而非服务端
2. 服务端已经通过 `currentConvId` 跟踪真正的 session
3. 刷新页面后，前端列表与实际对话不一致

### 修复方案

移除 `finalize()` 函数中的 `addConversation()` 调用，让对话管理完全由服务端负责。

```javascript
var isFinalizing = false;
function finalize() {
  if (isFinalizing) return;
  isFinalizing = true;
  try {
    render();
    // 注意：不要在这里添加对话到列表
    // 对话应该由服务端通过 /api/conversations 接口管理
    // currentConvId 已与服务端 session 关联
  } finally {
    currentMsg = null;
    currentBubble = null;
    buffer = '';
    toolCalls = [];
    toolStartTime = null;
    isFinalizing = false;
  }
}
```

---

## 问题3: 消息内容重复

### 根因分析

消息处理流程：
1. `onChunk()` 接收流式文本，累积到 `buffer`
2. `onDone()` 或 `onResponse()` 再次设置或追加 `buffer`

如果 LLM 返回的最终内容与之前流式传输的内容相同，会导致重复显示。

### 修复方案

在 `onDone` 和 `onResponse` 中添加内容去重检查：

```javascript
function onDone(data) {
  if (data.content) {
    var filtered = filterThink(data.content);
    if (filtered) {
      if (!currentMsg) createMsg();
      // 检查是否已经包含相同内容，避免重复
      if (buffer.indexOf(filtered) === -1) {
        buffer = filtered;
      }
      render();
    }
  }
  finalize();
  enableInput();
}

function onResponse(data) {
  if (!currentMsg) createMsg();

  // ... 工具调用处理 ...

  if (data.content) {
    var filtered = filterThink(data.content);
    if (filtered) {
      // 检查是否已经包含相同内容，避免重复
      if (buffer.indexOf(filtered) === -1) {
        buffer += filtered;
      }
      render();
    }
  }

  finalize();
  enableInput();
}
```

---

## 问题4: 工具调用结果显示方式

### 根因分析

LLM 有时候会把工具调用结果直接包含在回复文本中，例如：

```
根据搜索结果，Python 3.12 的主要特性包括...
已搜索到 15 条结果
第 1 条: xxx
...
```

这些工具结果的原始输出被拼接到了 AI 回复中。

### 修复方案

#### 1. 扩展 `filterThink()` 函数

添加对常见工具调用格式的过滤：

```javascript
function filterThink(content) {
  if (!content) return '';
  // Filter think tags
  var thinkStart = '\uFE4F\uFE5F';
  var thinkEnd = '\uFE5F';
  return content
    .replace(new RegExp(thinkStart + '[\\s\\S]*?' + thinkEnd, 'g'), '')
    .replace(new RegExp(thinkStart, 'g'), '')
    .replace(new RegExp(thinkEnd, 'g'), '')
    // 过滤 <tool_call>...</tool_call> 标签（Claude Code 格式）
    .replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, '')
    // 过滤 【工具】...【工具结果】... 格式
    .replace(/【工具】[\s\S]*?【工具结果】/gi, '')
    // 过滤 🔧 工具名...  格式
    .replace(/🔧[\s\S]*?(?:完成|成功|失败|错误)/gi, '')
    .trim();
}
```

#### 2. 新增 `filterToolContent()` 函数

在渲染时过滤工具调用相关内容：

```javascript
function filterToolContent(content) {
  if (!content) return '';
  var result = content;

  // 遍历所有工具调用，过滤掉已知的工具结果
  for (var i = 0; i < toolCalls.length; i++) {
    var t = toolCalls[i];
    if (t.result) {
      // 移除工具结果
      var shortResult = t.result.substring(0, 100);
      if (shortResult && result.indexOf(shortResult) !== -1) {
        result = result.replace(t.result, '');
      }
      // 移除包含常见工具结果前缀的内容
      result = result.replace(
        new RegExp('(?:已读取|已写入|已搜索|已执行|成功|失败|错误):[\\s\\S]*?(?=\\n|$)', 'gi'),
        ''
      );
    }
  }

  // 移除常见的工具调用输出格式
  result = result
    .replace(/^Tool:.*$/gim, '')
    .replace(/^Arguments:[\s\S]*?$/gim, '')
    .replace(/^Result:[\s\S]*?$/gim, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return result;
}
```

#### 3. 修改 `render()` 函数

使用过滤后的内容渲染：

```javascript
function render() {
  // ... 工具调用卡片渲染 ...

  // 过滤 buffer 中的工具调用相关内容
  var cleanBuffer = filterToolContent(buffer);

  if (cleanBuffer) {
    html += marked.parse(cleanBuffer);
  }

  currentBubble.innerHTML = html;
  // ...
}
```

---

## 修改文件汇总

| 文件 | 修改内容 |
|------|----------|
| `channels/websocket.py` | 添加 `_save_tool_call()` 保存工具调用到数据库 |
| `channels/chat.html` | 修复空对话、消息重复、工具结果显示问题 |

---

## 验证方法

### 1. 启动服务

```bash
cd E:\产品\Plector
python channels/websocket.py
```

### 2. 访问 Chat 页面

```
http://localhost:8080/chat
```

### 3. 测试场景

#### 场景1: 工具调用持久化

1. 发送一条会触发工具的消息（如搜索）
2. 观察工具调用卡片显示
3. **刷新页面**
4. 切换到该对话
5. 验证工具调用仍然显示

#### 场景2: 对话列表正确性

1. 发送消息，观察回复
2. 观察历史对话列表
3. 验证没有出现空对话或重复对话

#### 场景3: 内容无重复

1. 发送消息触发工具调用
2. 观察 AI 回复
3. 验证回复内容没有重复（同一句话出现两次）

#### 场景4: 工具结果正确分离

1. 发送搜索类消息
2. 观察工具结果是否只在卡片中显示
3. 验证主消息中没有原始的工具输出

---

## 相关文档

- [[79_v2.x_流式响应-工具可视化实现方案]]
- [[23_v1.2_WebSocket_Dashboard实现]]
- [[60_BRD_商业需求文档]]

---

## 更新记录

| 日期 | 版本 | 描述 |
|------|------|------|
| 2026-04-18 | v2.x | 初始版本，修复4个问题 |
