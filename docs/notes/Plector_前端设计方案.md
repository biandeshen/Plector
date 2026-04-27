---
tags: [Plector, 前端设计, 集成方案]
type: guide
created: 2026-04-27
related:
  - [PRD SPEC_INDEX](../specs/PRD/SPEC_INDEX.md)
  - docs/specs/Design_Plector.md
  - docs/notes/Plector_LobeChat_集成方案.md
---

# Plector 前端设计方案

> 基于 DeepSeek Chat 对话内容整理
> 来源：https://chat.deepseek.com/share/5oy46vadmw2vkhi1lh

---

## 一、前端需求与功能

### 1.1 核心功能模块

| 功能模块 | 说明 | 优先级 |
|----------|------|--------|
| 聊天交互 | 用户输入 → 发送后端 → 流式接收回复（Markdown、代码高亮） | P0 |
| 工具调用可视化 | 展示 Agent 调用的工具、输入参数、输出结果 | P0 |
| 记忆管理界面 | 查看、编辑、删除记忆 | P1 |
| 会话管理 | 创建/切换/删除会话，保留历史对话 | P1 |
| 技能与工具列表 | 动态展示 11 个技能和 59 个工具 | P1 |
| 系统状态监控 | 实时显示 ReAct 循环步骤、LLM 调用次数、Token 消耗 | P2 |
| 配置管理 | 切换 LLM 后端（Ollama/OpenAI/Anthropic）、调整参数 | P2 |

### 1.2 技术选型

| 组件 | 推荐技术 | 说明 |
|------|----------|------|
| 前端框架 | Vue 3 / React | 组件化开发 |
| UI 组件库 | Ant Design / Element Plus / Chakra UI | 快速构建 |
| 样式方案 | Tailwind CSS | 快速构建 UI |
| 通信协议 | WebSocket | 流式输出 |
| Markdown | react-markdown / vue-markdown | 渲染支持 |
| 代码高亮 | Prism.js / Highlight.js | 代码展示 |

---

## 二、后端接口协议

### 2.1 WebSocket 服务

```
地址: ws://localhost:8080
启动命令: python channels/websocket.py
```

### 2.2 消息类型定义

```typescript
interface PlectorMessage {
  type: 'user_message' | 'agent_start' | 'text_delta' | 'tool_call' | 'agent_end';
  content?: string;
  tool?: string;
  input?: any;
  output?: any;
  session_id?: string;
}
```

### 2.3 消息流程

```
用户输入 → user_message → 后端处理 → agent_start → text_delta (流式) → tool_call → agent_end
```

---

## 三、前端架构建议

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    表现层 (UI Layer)                     │
│  聊天界面 │ 工具卡片 │ 记忆管理 │ 系统监控 │ 配置面板   │
└─────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────┐
│                    状态层 (State Layer)                  │
│  会话状态 │ 消息列表 │ 工具执行状态 │ 用户配置         │
└─────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────┐
│                    服务层 (Service Layer)                │
│  WebSocket 服务 │ API 适配 │ 流式处理                  │
└─────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Plector Core                          │
│  AgentLoop + EventBus + SkillRegistry + ClosureEngine   │
└─────────────────────────────────────────────────────────┘
```

### 3.2 组件结构

```
src/
├── components/
│   ├── Chat/              # 聊天相关组件
│   │   ├── ChatInput.vue
│   │   ├── MessageList.vue
│   │   ├── MessageItem.vue
│   │   └── MarkdownRenderer.vue
│   ├── Tools/             # 工具可视化
│   │   ├── ToolCard.vue
│   │   └── ToolCallFlow.vue
│   ├── Memory/            # 记忆管理
│   ├── Session/           # 会话管理
│   ├── Skills/            # 技能列表
│   └── Dashboard/         # 系统监控
├── services/
│   ├── plectorService.ts   # WebSocket 服务
│   └── api.ts             # REST API
├── stores/
│   ├── chat.ts            # 聊天状态
│   ├── session.ts         # 会话状态
│   └── config.ts          # 用户配置
└── App.vue
```

---

## 四、集成方案对比

### 4.1 自研前端 vs 使用现有框架

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **自研前端** | 完全可控、定制灵活 | 工作量大 | 长期项目、独特需求 |
| **Lobe Chat** | 开箱即用、插件丰富 | 定制受限 | 快速上线、通用需求 |
| **Dify** | 低代码、全家桶 | 绑定平台 | 非技术用户 |

### 4.2 推荐方案

**阶段一（快速验证）**：基于 Lobe Chat 定制
**阶段二（长期规划）**：自研前端

---

## 五、Lobe Chat 集成方案

详见：`docs/notes/Plector_LobeChat_集成方案.md`

---

## 六、WebSocket 适配代码

详见：`docs/notes/Plector_WebSocket_适配代码.md`

---

**版本历史**：
- v1.0.0 (2026-04-27)：初始版本，基于 DeepSeek Chat 对话整理
