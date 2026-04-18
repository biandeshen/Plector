<template>
  <aside class="sidebar" :class="{ open: isOpen }">
    <div class="sidebar-top">
      <button class="new-chat-btn" @click="chatStore.newChat()">新对话</button>
    </div>
    <div class="sidebar-search">
      <SearchInput v-model="chatStore.searchQuery" />
    </div>
    <div class="conversations-header">
      <span>历史对话</span>
    </div>
    <div class="conversations-list">
      <ConversationItem
        v-for="conv in chatStore.filteredConversations"
        :key="conv.id"
        :conversation="conv"
        :is-active="conv.id === chatStore.currentConversationId"
        @select="onSelect"
        @delete="onDelete"
        @rename="onRename"
      />
    </div>
  </aside>
  <!-- 移动端遮罩 -->
  <div v-if="isOpen" class="sidebar-overlay" @click="$emit('close')"></div>
</template>

<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import SearchInput from './SearchInput.vue'
import ConversationItem from './ConversationItem.vue'

defineProps<{ isOpen: boolean }>()
const emit = defineEmits<{ close: [] }>()

const chatStore = useChatStore()

function onSelect(id: string) {
  chatStore.selectConversation(id)
  emit('close')
}

function onDelete(id: string) {
  if (confirm('确定删除该对话？')) {
    chatStore.removeConversation(id)
  }
}

function onRename(id: string, title: string) {
  chatStore.renameConversation(id, title)
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-top {
  padding: 12px;
  border-bottom: 1px solid var(--border);
}
.new-chat-btn {
  width: 100%;
  padding: 10px 16px;
  background: var(--accent);
  color: var(--bg);
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-align: center;
  transition: opacity var(--transition-fast);
}
.new-chat-btn:hover { opacity: 0.85; }
.sidebar-search {
  padding: 8px 12px 0;
}
.conversations-header {
  padding: 12px 16px 8px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
}
.conversations-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 8px;
}
.sidebar-overlay {
  display: none;
}
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -280px;
    top: 0;
    bottom: 0;
    z-index: 100;
    transition: left var(--transition-normal);
  }
  .sidebar.open { left: 0; }
  .sidebar-overlay {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 99;
  }
}
</style>
