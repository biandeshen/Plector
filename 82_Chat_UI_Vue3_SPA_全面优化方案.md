---
tags: [plector, chat-ui, vue3, spa, 优化方案]
date: 2026-04-18
updated: 2026-04-18
status: 实施中
phase: Phase 2 - Vite + Vue 3 SPA
---

# Plector Chat UI 全面优化方案

## 一、现状分析

### 1.1 当前架构

| 维度 | 现状 |
|------|------|
| 技术栈 | Vanilla JS + 内联 CSS，单 HTML 文件 (~1540 行) |
| 服务方式 | FastAPI `HTMLResponse(path.read_text())` |
| 状态管理 | 全局可变变量 (`currentMsg`, `buffer`, `toolCalls` 等) |
| 渲染方式 | 每次 chunk 重建整个 bubble 的 innerHTML |
| 外部依赖 | marked.js (Markdown)、highlight.js (代码高亮) |
| WebSocket | 8 种事件类型的实时流式通信 |

### 1.2 当前优势

- 轻量无框架，加载极快
- 暗色主题 CSS 变量体系设计合理
- 工具调用透明度高（思考/参数/结果完整展示）
- WebSocket 流式渲染体验流畅

### 1.3 当前痛点

- 全局状态耦合严重，`render()` 每次 chunk 重建整个 DOM
- 数据层和视图层没有分离，对话加载直接构造 DOM
- ES5 风格代码 (`var`, `XMLHttpRequest`)，维护成本高
- 无组件化，工具面板/消息/侧边栏逻辑交织在一起

---

## 二、与主流 AI 智能体对话框对比

### 2.1 功能对比矩阵

| 功能 | Plector | Qoder | ChatGPT | Claude | Gemini |
|------|---------|-------|---------|--------|--------|
| **工具调用展示** | | | | | |
| 折叠/展开动画 | 无动画硬切 | 平滑过渡 | 平滑过渡 | 平滑过渡 | 平滑过渡 |
| 执行进度指示 | 文字状态 | 旋转动画+进度条 | 旋转动画 | 旋转点 | 旋转动画 |
| 工具步骤编号 | 无 | 有序编号 | 无 | 有序编号 | 无 |
| 耗时统计 | 有(但格式粗糙) | 精细到ms | 无 | 无 | 无 |
| 全部折叠/展开 | 无 | 有 | 无 | 有 | 无 |
| 错误重试提示 | 无 | 有 | 有 | 有 | 有 |
| **消息体验** | | | | | |
| 停止生成按钮 | 无 | 有 | 有 | 有 | 有 |
| 重新生成 | 无 | 有 | 有 | 有 | 有 |
| 代码块语言标签 | 无 | 有 | 有 | 有 | 有 |
| 代码块独立复制 | 无 | 有 | 有 | 有 | 有 |
| 消息时间戳 | 无 | hover显示 | hover显示 | 有 | 有 |
| 流式光标 | 有(闪烁竖线) | 有 | 有(打字机) | 有 | 有 |
| **布局与交互** | | | | | |
| 移动端适配 | 无 | 有 | 有 | 有 | 有 |
| 侧边栏搜索 | 无 | 有 | 有 | 有 | 有 |
| 对话分组(日期) | 无 | 有 | 有 | 有 | 有 |
| 对话置顶/归档 | 无 | 无 | 无 | 有 | 无 |
| 键盘快捷键 | Enter发送 | 丰富快捷键 | Enter发送 | Enter发送 | Enter发送 |
| 主题切换 | 仅暗色 | 亮/暗 | 亮/暗/系统 | 亮/暗 | 亮/暗/系统 |
| 欢迎页建议提示词 | 无 | 有 | 有 | 有 | 有 |

### 2.2 关键差距总结

**P0 (必须有)**:
1. 停止生成按钮 - 所有主流产品标配
2. 代码块独立复制+语言标签 - 开发者体验核心
3. 工具面板折叠/展开过渡动画 - 体验差异最明显

**P1 (应该有)**:
4. 移动端响应式 - 用户场景覆盖
5. 侧边栏搜索 - 对话多了以后必需
6. 重新生成按钮 - 标准交互模式

**P2 (最好有)**:
7. 主题切换 (亮/暗)
8. 对话日期分组
9. 欢迎页建议提示词
10. 虚拟滚动 (长对话性能)

---

## 三、技术选型

### 3.1 框架选择：Vue 3

| 对比维度 | Vue 3 | React |
|----------|-------|-------|
| Python 团队学习曲线 | 低 (模板即 HTML) | 高 (JSX 心智模型不同) |
| CDN 即插即用能力 | 有 (官方支持) | 无 (CDN 模式已过时) |
| 流式数据响应式 | 内置 `ref()` 自动更新 | 需 `useState`+`useEffect` |
| 模板可读性 | HTML 增强语法 | JSX (全是 JavaScript) |
| 迁移摩擦 | 极低 (drop-in) | 高 (全面重写) |
| SFC 单文件组件 | 天然支持 | 无对应概念 |

**结论**: Vue 3 是最佳选择。理由：
1. 模板语法就是 HTML -- 对 Python 团队最友好
2. `ref()` 响应式天然适配 WebSocket 流 -- `buffer.value += chunk` 即自动更新 UI
3. CDN 模式可立即上手，无需构建工具
4. 当前全局变量直接映射为 `ref()` 值

### 3.2 部署策略

直接实施 Phase 2: Vite + Vue 3 SPA

- 前端目录: `frontend/`
- 构建输出: `frontend/dist/`
- 后端变更: `websocket.py` 添加 `StaticFiles` 挂载 `dist/`
- 遗留方案: `chat.html` 保留为 `chat_legacy.html` + `/chat-legacy` 路由

---

## 四、组件架构设计

### 4.1 组件树

```
App.vue
├── AppHeader.vue
│   ├── Logo + 导航 (监控 | 对话)
│   ├── ConnectionStatus.vue         (WebSocket 状态灯)
│   └── ThemeToggle.vue              (亮/暗主题切换)
│
├── ConversationSidebar.vue
│   ├── NewChatButton.vue
│   ├── SearchInput.vue              (对话搜索)
│   ├── ConversationGroup.vue        (按日期分组)
│   │   └── ConversationItem.vue     (标题、时间、重命名、删除)
│   └── SidebarToggle.vue            (移动端折叠)
│
├── ChatMain.vue
│   ├── WelcomeScreen.vue            (建议提示词)
│   ├── MessageList.vue              (虚拟滚动容器)
│   │   ├── UserMessage.vue
│   │   └── AssistantMessage.vue
│   │       ├── ToolSummaryPanel.vue (折叠面板，过渡动画)
│   │       │   └── ToolCallCard.vue (单个工具卡片)
│   │       │       ├── 思考区域
│   │       │       ├── 参数区域
│   │       │       └── 结果区域
│   │       ├── MarkdownContent.vue  (增量渲染)
│   │       ├── CodeBlock.vue        (语言标签+独立复制)
│   │       └── CopyButton.vue
│   └── ThinkingIndicator.vue
│
└── MessageInput.vue
    ├── AutoResizeTextarea.vue
    ├── SendButton.vue
    └── StopButton.vue               (停止生成)
```

### 4.2 状态管理设计

```
useChatStore (Pinia)
├── conversations[]              <- /api/conversations
├── currentConversationId
├── messages: Map<sessionId, Message[]>
├── streamingState
│   ├── isStreaming: boolean
│   ├── buffer: string           <- 累积文本
│   ├── toolCalls: ToolCall[]    <- 活跃工具调用
│   └── thinkingVisible: boolean
└── actions
    ├── loadConversations()
    ├── selectConversation(id)
    ├── appendChunk(content)     <- WebSocket chunk -> 自动触发 UI 更新
    ├── addToolCall(data)
    ├── updateToolCall(id, data)
    ├── finalizeMessage()        <- done 事件 -> 移入 messages
    └── stopGeneration()         <- 关闭 WebSocket 连接

useConnectionStore
├── status: 'connecting' | 'connected' | 'disconnected'
└── actions: connect(), disconnect(), send()
```

### 4.3 WebSocket -> Store 事件路由

```
WebSocket message -> routeEvent():
  'chunk'           -> chatStore.appendChunk(content)
  'toolExecuting'   -> chatStore.addToolCall(event)
  'toolDone'        -> chatStore.updateToolCall(toolId, event)
  'tool_call_start' -> chatStore.startToolCallBatch(count)
  'done'            -> chatStore.finalizeMessage(content)
  'response'        -> chatStore.handleBatchResponse(event)
  'error'           -> chatStore.handleError(event)
```

**核心改进**: 传输层(WebSocket)、状态层(Store)、渲染层(组件) 完全分离。

---

## 五、关键功能设计细节

### 5.1 工具调用卡片 (对标 Qoder + WorkBuddy)

**当前**: 硬切 `display:none/block`，无过渡
**优化**:

**默认行为**: 面板和卡片默认折叠，摘要行显示统计信息。

**摘要行格式** (对标 WorkBuddy):
```
▶ X 个工具调用，Y 条过程消息 (Z/X 完成)
```
- "过程消息"计数 = 含有 thinking 内容的工具调用数量
- 流式期间显示完成进度 `(done/total 完成)`
- ▶ 箭头展开时旋转 90° 变为 ▼

**折叠/展开过渡**:

```css
.tool-item-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease, opacity 0.2s ease;
  opacity: 0;
}
.tool-item-content.expanded {
  max-height: 500px;
  opacity: 1;
}
```

```html
<!-- Vue 模板 -->
<ToolCallCard v-for="(tool, i) in toolCalls" :key="tool.toolId">
  <template #header>
    <span class="step-number">{{ i + 1 }}</span>
    <span class="tool-name">{{ tool.name }}</span>
    <ToolStatus :status="tool.status" />
    <span class="elapsed" v-if="tool.elapsed">{{ tool.elapsed }}s</span>
    <ChevronIcon :expanded="tool.isExpanded" />
  </template>
  <template #content>
    <Transition name="slide">
      <div v-show="tool.isExpanded" class="tool-details">
        <ThinkingBlock v-if="tool.thinking" :text="tool.thinking" />
        <ArgsBlock v-if="tool.arguments" :args="tool.arguments" />
        <ResultBlock v-if="tool.result" :result="tool.result" />
      </div>
    </Transition>
  </template>
</ToolCallCard>
```

**ToolStatus 组件**:
- `running` -> 旋转 spinner 动画
- `done` -> 绿色勾 + 滑入动画
- `error` -> 红色叉 + 抖动动画

### 5.2 代码块增强 (对标 ChatGPT)

```
+------------------------------------------+
| python                          [Copy]   |
+------------------------------------------+
| def hello():                             |
|     print("Hello, World!")               |
+------------------------------------------+
```

- 语言标签显示在左上角
- 独立复制按钮在右上角
- hover 时复制按钮淡入
- 复制后显示 "已复制" 反馈

### 5.3 停止生成按钮

```
[发送中...] <- 输入框变为禁用
         [停止生成] <- 替代发送按钮
```

- 点击后关闭当前 WebSocket 连接并重新建立
- 保留已生成的部分内容
- 恢复输入框可用状态

### 5.4 移动端响应式

```css
@media (max-width: 768px) {
  .sidebar { 
    position: fixed; left: -280px; z-index: 100;
    transition: left 0.3s ease;
  }
  .sidebar.open { left: 0; }
  .message { max-width: 95%; }
  .input-area { padding: 8px 12px; }
}
```

### 5.5 Markdown 增量渲染优化

**当前问题**: 每次 chunk 对整个 buffer 调用 `marked.parse()`
**优化方案**: "稳定前缀 + 活跃尾部"

1. 维护 "已提交前缀" -- 在段落/块边界处截断的 markdown
2. 维护 "活跃尾部" -- 最后一个未完成的行/块
3. 每次 chunk:
   - 从末尾反向扫描找到最后一个 `\n\n` 安全断点
   - 断点前 = "已提交前缀" -> 解析一次，缓存 HTML
   - 断点后 = "活跃尾部" -> 每次重新解析 (很小，很快)
4. 渲染输出 = `缓存前缀HTML + 新解析尾部HTML + <StreamingCursor/>`

---

## 六、CSS 架构

### 6.1 设计系统 (保留并扩展现有变量)

```css
:root {
  /* 现有色彩 (保持不变) */
  --bg: #0f172a;
  --surface: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --accent: #38bdf8;

  /* 新增: 过渡动画 */
  --transition-fast: 150ms ease;
  --transition-normal: 300ms ease;
  --transition-slow: 500ms ease;

  /* 新增: 圆角体系 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* 新增: 间距体系 */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
}

/* 亮色主题 */
[data-theme="light"] {
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e2e8f0;
  --text: #1e293b;
  --text-muted: #64748b;
}
```

### 6.2 不使用 Tailwind

理由:
- 现有 CSS 变量体系已经是轻量设计系统
- 组件数量少 (~15个)，Tailwind 收益低
- Python 团队不需要额外学习 Tailwind 语法
- 模板中中文文本会被长 class 字符串淹没

---

## 七、实施步骤 (Phase 2: Vite + Vue 3 SPA)

1. `npm create vite@latest frontend -- --template vue-ts`
2. 安装依赖: `pinia`, `marked`, `highlight.js`
3. 创建组件架构 (参见 4.1 组件树)
4. 实现 Pinia stores (useChatStore, useConnectionStore)
5. 实现 WebSocket composable + 事件路由
6. 实现消息渲染组件 (Markdown/代码块/工具卡片)
7. 实现 P0 功能 (停止生成/代码块增强/工具卡片动画)
8. 实现 P1 功能 (移动端响应式/侧边栏搜索/重新生成)
9. 实现 P2 功能 (主题切换/日期分组/虚拟滚动)
10. 配置 Vite 代理 (`/ws` -> FastAPI, `/api/*` -> FastAPI)
11. 更新 `websocket.py` 添加 `StaticFiles` 挂载
12. 保留 `chat.html` 为 `chat_legacy.html` 作为回退方案
13. 集成测试与验证

---

## 八、风险控制

| 风险 | 缓解措施 |
|------|---------|
| 流式行为回归 | 保留 `chat_legacy.html` + `/chat-legacy` 路由做 A/B 对比 |
| `filterThink()` 复杂正则 | 原样迁移正则，添加单元测试 |
| 工具调用去重出错 | 新架构用 `Map<toolId, ToolCall>` 替代数组扫描 |
| 响应式开销 | Vue 3 proxy 响应式比 "重建 innerHTML" 更快，净正收益 |

---

## 九、实施进度

### 9.1 已完成

| 日期 | 阶段 | 完成内容 |
|------|------|---------|
| 2026-04-18 | A-基础搭建 | Vite 6 + Vue 3 + TypeScript 项目脚手架、CSS 变量/动画/Markdown 样式 |
| 2026-04-18 | B-逻辑层 | useThinkFilter、useMarkdown、useAutoResize composables，api.ts REST 客户端 |
| 2026-04-18 | C-状态管理 | Pinia stores (connection.ts + chat.ts 含 13 个 actions)，useWebSocket composable |
| 2026-04-18 | D-组件层 | 15 个 Vue 组件：layout/chat/tools/input/sidebar 全部实现 |
| 2026-04-18 | E-应用壳 | App.vue、main.ts、index.html，构建通过 |
| 2026-04-18 | F-后端集成 | CORS 中间件、StaticFiles 挂载、chat_legacy 路由，104 个 pytest 通过 |

### 9.2 设计变更记录

#### 变更 1：工具面板默认折叠（2026-04-18）

**背景**: 对标 WorkBuddy UI，工具调用面板应默认折叠，仅显示摘要行。

**改动**:
- `ToolSummaryPanel.vue`: `isPanelExpanded` 默认值 `true` → `false`
- `stores/chat.ts` `addToolCall()`: 流式工具 `isExpanded: true` → `false`
- `services/api.ts`: 历史工具已经是 `isExpanded: false`（无需改动）

**效果**: 面板默认折叠，显示 "▶ X 个工具调用，Y 条过程消息"，点击展开。

#### 变更 2：新增"过程消息"计数（2026-04-18）

**背景**: WorkBuddy 在摘要行同时显示工具调用数和过程消息数，如 "24 个工具调用，49 条过程消息"。原设计仅显示 "使用了 X 个工具"。

**改动**:
- `ToolSummaryPanel.vue`: 新增 `processMessageCount` 计算属性，统计含有 thinking 内容的工具调用数量
- 摘要文本格式: `使用了 X 个工具` → `X 个工具调用，Y 条过程消息`
- 箭头图标: ▼ 上下翻转 → ▶ 右/下旋转（更符合折叠面板语义）

**数据来源**: `ToolCall.thinking` 字段非空即计为一条过程消息

### 9.3 待完成

- [ ] P1: 重新生成按钮
- [ ] P2: 对话日期分组
- [ ] P2: 欢迎页建议提示词
- [ ] P2: 虚拟滚动（长对话性能优化）
- [ ] 性能优化: Markdown 增量渲染（"稳定前缀 + 活跃尾部"方案）
- [ ] 代码分割: 解决 JS bundle > 500KB 的构建警告
