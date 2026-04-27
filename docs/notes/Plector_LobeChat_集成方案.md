---
tags: [Plector, LobeChat, 集成方案]
type: guide
created: 2026-04-27
related:
  - docs/notes/Plector_前端设计方案.md
  - docs/notes/Plector_WebSocket_适配代码.md
---

# Plector + Lobe Chat 完整集成方案

> 基于 DeepSeek Chat 对话内容整理
> 来源：https://chat.deepseek.com/share/5oy46vadmw2vkhi1lh

---

## 一、Lobe Chat 简介

### 1.1 定位
现代化 AI 聊天应用框架，插件丰富，支持多种模型接入

### 1.2 特点
- 开源免费
- 支持 OpenAI API 格式
- 插件系统强大
- 主题丰富

---

## 二、集成方案概览

整个方案遵循 **"接入 → 适配 → 融入"** 的步骤：

1. **接入模型**：将 Plector 服务端作为自定义模型服务商接入 Lobe Chat
2. **适配协议**：通过修改核心代码或编写代理服务，解决 HTTP 与 WebSocket 的通信问题
3. **功能融入**：利用 Lobe Chat 的插件系统，将 Plector 的工具调用、记忆管理等功能展现在前端

---

## 三、实施路线图

| 阶段 | 步骤 | 内容 | 优先级 |
|------|------|------|--------|
| **阶段一** | ① 环境准备 | Node.js 18+, pnpm | P0 |
| | ② 获取源码 | git clone https://github.com/lobehub/lobe-chat.git | P0 |
| | ③ 配置环境变量 | .env.local | P0 |
| | ④ 启动开发服务 | pnpm dev | P0 |
| | ⑤ 添加自定义模型 | 修改服务商配置 | P0 |
| **阶段二** | ⑥ 核心适配 | 方案A: 单向代理 / 方案B: 双向中继 | P0 |
| **阶段三** | ⑦ 插件开发 | 接入 Plector 工具 | P1 |
| | ⑧ 插件上架 | 本地测试 | P1 |
| | ⑨ UI 定制 | 主题与布局 | P2 |

---

## 四、阶段一：基础部署与配置

### 4.1 环境准备

```bash
# 安装 Node.js 18+
node -v  # 确认 >= 18.0.0

# 安装 pnpm
npm install -g pnpm
pnpm -v
```

### 4.2 获取源码

```bash
git clone https://github.com/lobehub/lobe-chat.git
cd lobe-chat
pnpm install
```

### 4.3 配置环境变量

```ini
# .env.local 文件内容

# 关键：将这行注释掉或设为空，防止 Lobe Chat 直接调用 OpenAI
# OPENAI_API_KEY=sk-...

# 新增：标记我们使用的是自定义后端
CUSTOM_MODELS=+plector://plector?token=dummy

# 允许无 API Key 模式
ALLOW_EMPTY_SETTINGS=true
```

### 4.4 启动开发服务

```bash
pnpm dev
# 访问 http://localhost:3000
```

### 4.5 添加自定义模型

在设置中添加自定义模型服务商，配置：
- 模型名称：`plector` 或 `custom-plector`
- API 地址：`http://localhost:8080`（或你的 Plector WebSocket 地址）

---

## 五、阶段二：WebSocket 适配（核心步骤）

### 方案 A（推荐）：单向代理

**核心思想**：让 Lobe Chat 将请求转发给一个特定的 API 路由，然后在这个路由里将 HTTP 请求转换成 WebSocket 消息发送给 Plector。

```typescript
// src/app/api/plector/route.ts

import { NextRequest } from 'next/server';
import { PlectorWebSocket } from '@/services/plectorService';

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { messages, session_id } = body;

  // 创建 WebSocket 连接
  const plector = new PlectorWebSocket(session_id || 'default');

  return new Response(
    new ReadableStream({
      async start(controller) {
        plector.connect(
          () => {
            // 发送用户消息
            plector.sendUserMessage(messages[messages.length - 1].content);
          },
          (data) => {
            // 将 Plector 消息转换为 SSE 格式
            if (data.type === 'text_delta') {
              controller.enqueue(`data: ${JSON.stringify({ choices: [{ delta: { content: data.content } }] })}\n\n`);
            } else if (data.type === 'agent_end') {
              controller.close();
            }
          },
          (err) => {
            console.error(err);
            controller.close();
          },
          () => {
            controller.close();
          }
        );
      },
    }),
    {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    }
  );
}
```

### 方案 B：独立中继

编写一个独立的 Web 服务作为中转站：

```python
# relay_server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            # 转发到 Plector
            # 处理响应并返回
    except WebSocketDisconnect:
        pass

@app.post("/v1/chat/completions")
async def chat_completions(req: Request):
    # 将 HTTP 请求转换为 WebSocket 消息
    # 返回 SSE 流
    pass
```

---

## 六、阶段三：功能融合与定制

### 6.1 插件开发

Lobe Chat 的插件系统本质上是 **Function Calling** 的标准化扩展。

**开发一个插件的典型流程**：

```typescript
import { definePlugin } from 'lobe-chat-plugin-sdk';

export default definePlugin({
  name: 'Plector Web Search',
  description: '使用 Plector 引擎进行网页搜索',
  parameters: [
    {
      name: 'query',
      type: 'string',
      required: true,
      description: '搜索关键词'
    }
  ],
  async execute({ query }) {
    const result = await callPlectorWebSocket({
      type: 'tool_call',
      tool: 'web_search',
      input: { query }
    });
    return `您的查询 "${query}" 的搜索结果是：${result}`;
  },
});
```

### 6.2 UI 定制

- **主题定制**：修改 Tailwind CSS 配置
- **布局调整**：自定义组件位置
- **功能增强**：添加 Plector 特有功能

---

## 七、进阶玩法

### 7.1 深度集成 Plector 工具

利用 Lobe Chat 的函数调用能力，将 Plector 的 11 个技能和 59 个工具深度集成：

```typescript
// 注册 Plector 工具到 Lobe Chat
const tools = [
  {
    name: 'plector_web_search',
    description: '使用 Plector 进行网页搜索',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string' }
      }
    }
  },
  // ... 其他工具
];
```

### 7.2 记忆可视化

将 Plector 的记忆系统与 Lobe Chat 的会话管理深度结合：

- 展示记忆向量相似度
- 可视化记忆检索过程
- 编辑/删除记忆

---

## 八、总结

| 阶段 | 核心任务 | 产出 |
|------|----------|------|
| **阶段一** | 本地部署 Lobe Chat | 可运行的前端 |
| **阶段二** | 攻克 HTTP/WebSocket 适配 | 消息互通 |
| **阶段三** | 插件开发 + UI 定制 | 功能完整的前端 |

**推荐路径**：
1. **第一步**：快速本地部署 Lobe Chat，将 Plector 配置为自定义后端（接入）
2. **第二步**：攻克技术核心，通过适配层解决 HTTP 与 WebSocket 的通信问题
3. **第三步**：利用 Lobe Chat 的插件系统，将 Plector 的独特功能和工具"无缝融入"

---

**版本历史**：
- v1.0.0 (2026-04-27)：初始版本
