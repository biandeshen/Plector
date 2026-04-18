<template>
  <button class="theme-toggle" @click="toggle" :title="isDark ? '切换亮色' : '切换暗色'">
    {{ isDark ? '☀️' : '🌙' }}
  </button>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const isDark = ref(true)

function toggle() {
  isDark.value = !isDark.value
  document.documentElement.dataset.theme = isDark.value ? 'dark' : 'light'
  localStorage.setItem('plector-theme', isDark.value ? 'dark' : 'light')
}

onMounted(() => {
  const saved = localStorage.getItem('plector-theme')
  if (saved === 'light') {
    isDark.value = false
    document.documentElement.dataset.theme = 'light'
  }
})
</script>

<style scoped>
.theme-toggle {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 14px;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.theme-toggle:hover {
  background: var(--surface-2);
}
</style>
