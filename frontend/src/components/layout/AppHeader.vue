<template>
  <header class="header">
    <div class="header-left">
      <button class="sidebar-toggle-btn" @click="$emit('toggle-sidebar')">☰</button>
      <h1>Plector</h1>
    </div>
    <nav class="header-nav">
      <a class="nav-btn" href="/">监控</a>
      <a class="nav-btn active" href="/chat">对话</a>
    </nav>
    <div class="header-status">
      <ConnectionStatus :status="connectionStore.status" />
      <ThemeToggle />
    </div>
  </header>
</template>

<script setup lang="ts">
import { useConnectionStore } from '@/stores/connection'
import ConnectionStatus from './ConnectionStatus.vue'
import ThemeToggle from './ThemeToggle.vue'

defineEmits<{ 'toggle-sidebar': [] }>()

const connectionStore = useConnectionStore()
</script>

<style scoped>
.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-left h1 {
  font-size: 18px;
  font-weight: 600;
  color: var(--accent);
}
.sidebar-toggle-btn {
  display: none;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
}
.header-nav {
  display: flex;
  gap: 8px;
}
.nav-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
}
.nav-btn:hover {
  background: var(--surface-2);
  color: var(--text);
  text-decoration: none;
}
.nav-btn.active {
  background: var(--accent);
  color: var(--bg);
  border-color: var(--accent);
}
.header-status {
  display: flex;
  align-items: center;
  gap: 12px;
}
@media (max-width: 768px) {
  .sidebar-toggle-btn { display: block; }
  .header-nav { display: none; }
}
</style>
