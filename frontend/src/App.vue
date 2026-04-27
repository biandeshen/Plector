<template>
  <AppHeader @toggle-sidebar="sidebarOpen = !sidebarOpen" />
  <div class="main">
    <ConversationSidebar :is-open="sidebarOpen" @close="sidebarOpen = false" />
    <ChatMain />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import AppHeader from '@/components/layout/AppHeader.vue'
import ConversationSidebar from '@/components/sidebar/ConversationSidebar.vue'
import ChatMain from '@/components/chat/ChatMain.vue'

useWebSocket()

const sidebarOpen = ref(false)
</script>

<style scoped>
.main {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
  /* height: auto + flex: 1 allows content to determine height,
     but max-height: 100vh should constrain it */
  max-height: 100vh;
}
</style>
