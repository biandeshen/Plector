<template>
  <div class="messages" ref="messagesRef">
    <template v-for="msg in messages" :key="msg.id">
      <UserMessage v-if="msg.role === 'user'" :content="msg.content" />
      <AssistantMessage v-else :message="msg" />
    </template>

    <!-- 流式消息 -->
    <template v-if="chatStore.isStreaming">
      <ThinkingIndicator v-if="chatStore.streamIsThinking" />
      <AssistantMessage
        v-else
        :stream-buffer="chatStore.streamBuffer"
        :stream-tool-calls="chatStore.orderedToolCalls"
        :is-streaming="true"
        :is-finalizing="chatStore.streamIsFinalizing"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import type { Message } from '@/types'
import { useChatStore } from '@/stores/chat'
import UserMessage from './UserMessage.vue'
import AssistantMessage from './AssistantMessage.vue'
import ThinkingIndicator from './ThinkingIndicator.vue'

defineProps<{ messages: Message[] }>()

const chatStore = useChatStore()
const messagesRef = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

// 流式内容变化时自动滚动
watch(() => chatStore.streamBuffer, scrollToBottom)
watch(() => chatStore.orderedToolCalls.length, scrollToBottom)
watch(() => chatStore.currentMessages.length, scrollToBottom)

onMounted(scrollToBottom)
</script>

<style scoped>
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
