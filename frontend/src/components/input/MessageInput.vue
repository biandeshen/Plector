<template>
  <div class="input-area">
    <textarea
      ref="textareaRef"
      v-model="inputText"
      placeholder="输入消息..."
      rows="1"
      :disabled="chatStore.isStreaming"
      @keydown="onKeydown"
    ></textarea>
    <button
      v-if="chatStore.isStreaming"
      class="stop-btn"
      @click="chatStore.stopGeneration()"
    >
      &#9632; 停止生成
    </button>
    <button
      v-else
      class="send-btn"
      :disabled="!inputText.trim()"
      @click="sendMessage"
    >
      发送
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useConnectionStore } from '@/stores/connection'
import { useAutoResize } from '@/composables/useAutoResize'

const chatStore = useChatStore()
const connectionStore = useConnectionStore()
const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

useAutoResize(textareaRef)

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return

  inputText.value = ''
  // 重置 textarea 高度
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }

  // 确保有对话
  if (!chatStore.currentConversationId) {
    await chatStore.createNewConversation()
  }

  // 添加用户消息到 UI
  chatStore.addUserMessage(text)
  // 初始化流式状态
  chatStore.initStreaming()

  // 通过 WebSocket 发送
  connectionStore.send({
    content: text,
    session_id: chatStore.currentConversationId,
  })
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    sendMessage()
  }
}
</script>

<style scoped>
.input-area {
  padding: 12px 32px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}
.input-area textarea {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 14px;
  color: var(--text);
  font-size: 14px;
  font-family: var(--font-sans);
  resize: none;
  outline: none;
  min-height: 40px;
  max-height: 160px;
}
.input-area textarea:focus { border-color: var(--accent); }
.input-area textarea::placeholder { color: var(--text-weak); }
.send-btn {
  background: var(--btn);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.send-btn:hover { background: var(--btn-hover); }
.send-btn:disabled { background: var(--border); color: var(--text-weak); cursor: not-allowed; }
.stop-btn {
  background: var(--red);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
  white-space: nowrap;
}
.stop-btn:hover { opacity: 0.85; }
@media (max-width: 768px) {
  .input-area { padding: 8px 12px; }
}
</style>
