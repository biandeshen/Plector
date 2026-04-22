# Plector Chat 页面补全方案（Claude Code 可执行版）

> 目标：
>   在现有 chat.html 基础上补全 6 个缺失功能
>   不重写已有代码，只在关键位置插入/修改
>
> 改动文件：
>   channels/websocket.py（修改：🤔过滤 + 工具结果清理 + 消息保存）
>   channels/chat.html（修改：停止生成 + 代码块增强 + 工具面板动画）
>
> 共 5 步，按顺序执行。

---

## 第一步：修改 websocket.py（后端）

### 1.1 添加 🤔 过滤函数

在文件顶部 import 区域后添加：

```python
import re


def filter_think_tags(content: str) -> str:
    """过滤 🤔...</think> 标签及其内容"""
    if not content:
        return content
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    content = re.sub(r'<think>.*', '', content, flags=re.DOTALL).strip()
    return content


def clean_tool_result(result) -> str:
    """
    清理工具结果，去掉 JSON-RPC 外壳，提取有用字段

    输入:
        {"jsonrpc": "2.0", "result": {"success": True, "data": {...}, "error": None}}

    输出:
        有用的数据部分
    """
    if result is None:
        return ""

    # 如果是字符串，尝试解析
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return result

    # 如果不是字典，直接返回
    if not isinstance(result, dict):
        return str(result)

    # JSON-RPC 格式: {"jsonrpc": "2.0", "result": {...}}
    if "jsonrpc" in result and "result" in result:
        inner = result["result"]
        if isinstance(inner, dict):
            # Plector 格式: {"success": bool, "data": any, "error": str}
            if "success" in inner and "data" in inner:
                if inner.get("success") and inner.get("data"):
                    return _format_data(inner["data"])
                elif inner.get("error"):
                    return f"错误: {inner['error']}"
                else:
                    return "执行完成（无返回数据）"
            return _format_data(inner)
        return str(inner)

    # Plector 格式直接
    if "success" in result and "data" in result:
        if result.get("success") and result.get("data"):
            return _format_data(result["data"])
        elif result.get("error"):
            return f"错误: {result['error']}"
        else:
            return "执行完成（无返回数据）"

    return _format_data(result)


def _format_data(data) -> str:
    """格式化数据为可读        return data
    if isinstance(data, list):
        if len(data) == 0:
            return "空结果"
        # 列表项如果是字典，尝试提取关键字段
        items = []
        for item in data[:10]:  # 最多显示 10 条
            if isinstance(item, dict):
                # 优先显示 title/name/content
                for key in ["title", "name文本"""
    if isinstance(data, str):
", "content", "description", "text"]:
                    if key in item:
                        items.append(str(item[key])[:200])
                        break
                else:
                    items.append(json.dumps(item, ensure_ascii=False)[:200])
            else:
                items.append(str(item)[:200])
        result = "\n".join(f"• {item}" for item in items)
        if len(data) > 10:
            result += f"\n... 共 {len(data)} 条"
        return result
    if isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False, indent=2)[:2000]
    return str(data)[:2000]
```

### 1.2 在消息发送前过滤

找到 WebSocket 发送消息的代码位置（通常是 `await websocket.send_json(data)` 或类似），在发送前添加过滤：

```python
# 发送 AI 回复时
if "content" in response_data:
    response_data["content"] = filter_think_tags(response_data["content"])

# 发送工具结果时
if "result" in tool_data:
    tool_data["result"] = clean_tool_result(tool_data["result"])

await websocket.send_json(response_data)
```

### 1.3 添加消息保存 API

找到现有的对话相关 API，在其中添加消息保存逻辑：

```python
# 保存消息到对话
def save_message(conversation_id: str, message: dict):
    """保存消息到对话历史"""
    # 确保 conversations 目录存在
    conv_dir = Path("conversations")
    conv_dir.mkdir(exist_ok=True)

    conv_file = conv_dir / f"{conversation_id}.json"

    # 读取现有消息
    messages = []
    if conv_file.exists():
        try:
            messages = json.loads(conv_file.read_text(encoding="utf-8"))
        except Exception:
            messages = []

    # 添加新消息
    messages.append(message)

    # 保存
    conv_file.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")


# 获取对话消息
def get_messages(conversation_id: str) -> list:
    """获取对话历史消息"""
    conv_file = Path("conversations") / f"{conversation_id}.json"

    if not conv_file.exists():
        return []

    try:
        return json.loads(conv_file.read_text(encoding="utf-8"))
    except Exception:
        return []


# 对话列表 API
@app.get("/api/conversations")
async def list_conversations():
    """获取对话列表"""
    conv_dir = Path("conversations")
    if not conv_dir.exists():
        return []

    conversations = []
    for f in sorted(conv_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            messages = json.loads(f.read_text(encoding="utf-8"))
            # 获取第一条用户消息作为标题
            title = "新对话"
            for msg in messages:
                if msg.get("role") == "user":
                    title = msg.get("content", "")[:30]
                    break

            conversations.append({
                "id": f.stem,
                "title": title,
                "message_count": len(messages),
                "updated_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        except Exception:
            continue

    return conversations


# 获取对话详情 API
@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取对话详情"""
    messages = get_messages(conversation_id)
    return {"id": conversation_id, "messages": messages}


# 删除对话 API
@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    conv_file = Path("conversations") / f"{conversation_id}.json"
    if conv_file.exists():
        conv_file.unlink()
        return {"success": True}
    return {"success": False, "error": "对话不存在"}
```

### 1.4 在 WebSocket 处理中保存消息

找到 WebSocket 处理用户消息的地方，添加保存逻辑：

```python
async def _handle_websocket_message(message: dict, websocket: WebSocket):
    user_input = message.get("content", "")
    conversation_id = message.get("conversation_id", "default")

    # 保存用户消息
    save_message(conversation_id, {
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat(),
    })

    # 执行 Agent
    async for event in agent.run_streaming(user_input, conversation_id):
        # 过滤 🤔 标签
        if "content" in event:
            event["content"] = filter_think_tags(event["content"])

        # 清理工具结果
        if "result" in event:
            event["result"] = clean_tool_result(event["result"])

        await websocket.send_json(event)

        # 保存 AI 回复
        if event.get("type") == "done":
            save_message(conversation_id, {
                "role": "assistant",
                "content": event.get("content", ""),
                "tool_calls": event.get("tool_calls", []),
                "timestamp": datetime.now().isoformat(),
            })
```

### 验证

```bash
python -m py_compile channels/websocket.py
```

---

## 第二步：修改 chat.html（停止生成按钮）

### 2.1 添加停止按钮 CSS

在 `</think> 标签过滤 + 工具结果清理 + 消息保存）
- `channels/chat.html`（停止生成 + 代码块增强 + 工具面板动画）

### 新增功能

| 功能 | 说明 |
|------|------|
| 停止生成 | 用户可中断 AI 生成 |
| 代码块语言标签 | 显示语言名（python/bash/json） |
| 代码块独立复制 | 每个代码块有独立复制按钮 |
| 工具面板折叠动画 | 展开/折叠有滑动动画 |
| 🤔 标签过滤 | 后端过滤，前端不显示 |
| 工具结果清理 | 去掉 JSON-RPC 外壳 |
| 消息持久化 | 刷新后消息不丢失 |

### 设计文档对照

| 要求 | 状态 |
|------|------|
| 停止生成按钮 | ✅ 本次补全 |
| 代码块语言标签 | ✅ 本次补全 |
| 代码块独立复制 | ✅ 本次补全 |
| 工具面板折叠动画 | ✅ 本次补全 |
| 🤔 标签过滤 | ✅ 本次补全 |
| 工具结果清理 | ✅ 本次补全 |
| 消息持久化 | ✅ 本次补全 |
| WebSocket 状态指示 | ✅ 已有 |
| 暗色主题 | ✅ 已有 |
| 侧边栏搜索 | ✅ 已有 |
| 欢迎页建议卡片 | ✅ 已有 |
| 对话历史列表 | ✅ 已有 |
| 主题切换按钮 | ⚠️ 按钮存在但亮色主题未实现（P2） |

---

**从第一步开始执行，每步验证通过后再继续。**
```