<template>
  <div class="chat-area">
    <WelcomeScreen
      v-if="!chatStore.currentConversationId && !chatStore.isStreaming"
      @select="handleSuggestionSelect"
    />
    <MessageList v-else :messages="chatStore.currentMessages" />
    <MessageInput />
  </div>
</template>

<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import { useConnectionStore } from '@/stores/connection'
import WelcomeScreen from './WelcomeScreen.vue'
import MessageList from './MessageList.vue'
import MessageInput from '@/components/input/MessageInput.vue'

const chatStore = useChatStore()
const connectionStore = useConnectionStore()

async function handleSuggestionSelect(text: string) {
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
</script>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}
</style>
