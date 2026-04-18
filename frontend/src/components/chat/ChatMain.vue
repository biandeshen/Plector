<template>
  <div class="chat-area">
    <WelcomeScreen v-if="!chatStore.currentConversationId && !chatStore.isStreaming" />
    <MessageList v-else :messages="chatStore.currentMessages" />
    <MessageInput />
  </div>
</template>

<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import WelcomeScreen from './WelcomeScreen.vue'
import MessageList from './MessageList.vue'
import MessageInput from '@/components/input/MessageInput.vue'

const chatStore = useChatStore()
</script>

<style scoped>
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
