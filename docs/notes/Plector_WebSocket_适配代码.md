---
tags: [Plector, WebSocket, 前端, TypeScript]
type: code
created: 2026-04-27
related:
  - docs/notes/Plector_前端设计方案.md
  - docs/notes/Plector_LobeChat_集成方案.md
---

# Plector WebSocket 适配代码

> 基于 DeepSeek Chat 对话内容整理
> 来源：https://chat.deepseek.com/share/5oy46vadmw2vkhi1lh

---

## 一、WebSocket 服务模块

### 1.1 核心服务类

```typescript
// src/services/plectorService.ts

export interface PlectorMessage {
  type: 'user_message' | 'agent_start' | 'text_delta' | 'tool_call' | 'agent_end';
  content?: string;
  tool?: string;
  input?: any;
  output?: any;
  session_id?: string;
}

export interface ToolCallResult {
  tool: string;
  input: any;
  output: any;
  duration?: number;
}

export class PlectorWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  /**
   * 建立 WebSocket 连接
   */
  connect(
    onOpen?: () => void,
    onMessage?: (data: PlectorMessage) => void,
    onError?: (err: Event) => void,
    onClose?: () => void
  ) {
    const wsUrl = `ws://localhost:8080`; // 你的 Plector WebSocket 地址
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
      // 发送会话 ID 初始化
      this.ws?.send(
        JSON.stringify({
          type: 'init',
          session_id: this.sessionId,
        })
      );
      onOpen?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as PlectorMessage;
        onMessage?.(data);
      } catch (e) {
        console.error('❌ Failed to parse message', e);
      }
    };

    this.ws.onerror = (err) => {
      console.error('❌ WebSocket error', err);
      onError?.(err);
    };

    this.ws.onclose = () => {
      console.log('🔌 WebSocket closed');
      onClose?.();
    };
  }

  /**
   * 发送用户消息
   */
  sendUserMessage(content: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    this.ws.send(
      JSON.stringify({
        type: 'user_message',
        content,
        session_id: this.sessionId,
      })
    );
  }

  /**
   * 重连机制
   */
  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ Max reconnect attempts reached');
      return;
    }
    this.reconnectAttempts++;
    console.log(`🔄 Reconnecting... attempt ${this.reconnectAttempts}`);
    setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
  }

  /**
   * 关闭连接
   */
  close() {
    this.ws?.close();
  }

  /**
   * 检查连接状态
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
```

---

## 二、聊天服务适配

### 2.1 聊天函数扩展

```typescript
// src/services/chat.ts

import { PlectorWebSocket, PlectorMessage, ToolCallResult } from './plectorService';

interface ChatParams {
  model: string;
  messages: Array<{ role: string; content: string }>;
  signal?: AbortSignal;
  conversationId?: string;
  // ... 其他参数
}

// 全局存储活跃 WebSocket 连接（按会话ID）
const wsConnections: Map<string, PlectorWebSocket> = new Map();

export const chat = async (
  params: ChatParams
): Promise<AsyncIterable<any>> => {
  const { model, messages, signal, ...rest } = params;

  // 判断是否使用 Plector 后端
  if (model === 'plector' || model === 'custom-plector') {
    return plectorChatStream(params);
  }

  // 原有 OpenAI 逻辑...
  return openAIChatStream(params);
};

/**
 * Plector 流式聊天
 */
async function* plectorChatStream(
  params: ChatParams
): AsyncIterable<any> {
  const { messages, signal, conversationId } = params;
  const sessionId = conversationId || 'default';

  // 获取或创建 WebSocket 连接
  let ws = wsConnections.get(sessionId);
  if (!ws || !ws.isConnected()) {
    ws = new PlectorWebSocket(sessionId);
    wsConnections.set(sessionId, ws);
  }

  // 创建流式响应生成器
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();

      ws!.connect(
        () => {
          // 连接成功后发送用户消息
          const lastMessage = messages[messages.length - 1];
          ws!.sendUserMessage(lastMessage.content);
        },
        (data: PlectorMessage) => {
          // 处理收到的消息
          switch (data.type) {
            case 'agent_start':
              controller.enqueue(
                encoder.encode(`data: ${JSON.stringify({
                  choices: [{ delta: { content: '🤖 ' } }]
                })}\n\n`)
              );
              break;

            case 'text_delta':
              controller.enqueue(
                encoder.encode(`data: ${JSON.stringify({
                  choices: [{ delta: { content: data.content } }]
                })}\n\n`)
              );
              break;

            case 'tool_call':
              controller.enqueue(
                encoder.encode(`data: ${JSON.stringify({
                  choices: [{
                    delta: {
                      content: `\n🔧 工具调用: ${data.tool}\n`
                    }
                  }]
                })}\n\n`)
              );
              break;

            case 'agent_end':
              controller.close();
              wsConnections.delete(sessionId);
              break;
          }
        },
        (err) => {
          console.error('WebSocket error:', err);
          controller.error(err);
        },
        () => {
          controller.close();
        }
      );
    },
    cancel() {
      // 用户取消时关闭连接
      ws?.close();
      wsConnections.delete(sessionId);
    }
  });

  yield* stream;
}
```

---

## 三、工具调用可视化

### 3.1 工具卡片组件

```typescript
// src/components/Tools/ToolCard.vue

import { defineComponent, PropType } from 'vue';

interface ToolCallData {
  tool: string;
  input: any;
  output: any;
  duration?: number;
  timestamp: number;
}

export default defineComponent({
  name: 'ToolCard',
  props: {
    toolCall: {
      type: Object as PropType<ToolCallData>,
      required: true,
    },
  },
  setup(props) {
    const formatDuration = (ms?: number) => {
      if (!ms) return '-';
      return `${ms}ms`;
    };

    const formatOutput = (output: any) => {
      if (typeof output === 'string') return output;
      return JSON.stringify(output, null, 2);
    };

    return {
      formatDuration,
      formatOutput,
    };
  },
  template: `
    <div class="tool-card border rounded-lg p-4 mb-3 bg-gray-50">
      <div class="flex items-center justify-between mb-2">
        <span class="font-mono text-sm font-semibold text-blue-600">
          🔧 {{ toolCall.tool }}
        </span>
        <span class="text-xs text-gray-500">
          {{ formatDuration(toolCall.duration) }}
        </span>
      </div>

      <div v-if="toolCall.input" class="mb-2">
        <span class="text-xs text-gray-400">输入:</span>
        <pre class="text-xs bg-white p-2 rounded border mt-1 overflow-x-auto">{{ JSON.stringify(toolCall.input, null, 2) }}</pre>
      </div>

      <div v-if="toolCall.output" class="mb-2">
        <span class="text-xs text-gray-400">输出:</span>
        <pre class="text-xs bg-white p-2 rounded border mt-1 overflow-x-auto">{{ formatOutput(toolCall.output) }}</pre>
      </div>

      <div class="text-xs text-gray-400 mt-2">
        {{ new Date(toolCall.timestamp).toLocaleTimeString() }}
      </div>
    </div>
  `,
});
```

### 3.2 ReAct 循环可视化

```typescript
// src/components/Tools/ReActFlow.vue

import { defineComponent, ref, computed } from 'vue';

interface ReActStep {
  step: number;
  type: 'reason' | 'act' | 'observe';
  content: string;
  tool?: string;
  result?: any;
}

export default defineComponent({
  name: 'ReActFlow',
  props: {
    steps: {
      type: Array as PropType<ReActStep[]>,
      required: true,
    },
  },
  setup(props) {
    const getStepIcon = (type: string) => {
      switch (type) {
        case 'reason': return '🤔';
        case 'act': return '🔧';
        case 'observe': return '👁️';
        default: return '📝';
      }
    };

    const getStepColor = (type: string) => {
      switch (type) {
        case 'reason': return 'border-yellow-400 bg-yellow-50';
        case 'act': return 'border-blue-400 bg-blue-50';
        case 'observe': return 'border-green-400 bg-green-50';
        default: return 'border-gray-400 bg-gray-50';
      }
    };

    return {
      getStepIcon,
      getStepColor,
    };
  },
  template: `
    <div class="react-flow p-4">
      <div class="text-sm font-semibold mb-4">🔄 ReAct 循环</div>
      <div class="space-y-3">
        <div
          v-for="(step, index) in steps"
          :key="index"
          :class="['border-l-4 rounded p-3', getStepColor(step.type)]"
        >
          <div class="flex items-center gap-2 mb-1">
            <span class="text-lg">{{ getStepIcon(step.type) }}</span>
            <span class="font-medium">步骤 {{ step.step }}</span>
            <span class="text-xs px-2 py-0.5 rounded bg-gray-200">
              {{ step.type }}
            </span>
          </div>
          <div class="text-sm">{{ step.content }}</div>
          <div v-if="step.tool" class="mt-2 text-xs">
            <span class="font-mono bg-gray-200 px-1 rounded">{{ step.tool }}</span>
          </div>
          <div v-if="step.result" class="mt-2 text-xs bg-white p-2 rounded">
            {{ step.result }}
          </div>
        </div>
      </div>
    </div>
  `,
});
```

---

## 四、流式输出处理

### 4.1 Markdown 渲染

```typescript
// src/components/Chat/MarkdownRenderer.vue

import { defineComponent, PropType } from 'vue';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';

export default defineComponent({
  name: 'MarkdownRenderer',
  props: {
    content: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const renderers = {
      code({ node, inline, className, children, ...props }: any) {
        const match = /language-(\w+)/.exec(className || '');
        const codeString = String(children).replace(/\n$/, '');

        return !inline && match ? (
          <SyntaxHighlighter
            style={oneDark}
            language={match[1]}
            PreTag="div"
            {...props}
          >
            {codeString}
          </SyntaxHighlighter>
        ) : (
          <code className={className} {...props}>
            {children}
          </code>
        );
      },
    };

    return {
      renderers,
    };
  },
  template: `
    <div class="markdown-content">
      <ReactMarkdown :components="renderers">
        {{ content }}
      </ReactMarkdown>
    </div>
  `,
});
```

---

**版本历史**：
- v1.0.0 (2026-04-27)：初始版本
