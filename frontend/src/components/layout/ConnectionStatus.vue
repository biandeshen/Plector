<template>
  <span class="status-dot" :class="status"></span>
  <span class="status-text">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: 'connecting' | 'connected' | 'disconnected' }>()

const label = computed(() => {
  switch (props.status) {
    case 'connected': return '已连接'
    case 'connecting': return '连接中...'
    case 'disconnected': return '已断开'
  }
})
</script>

<style scoped>
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green);
  display: inline-block;
}
.status-dot.disconnected { background: var(--red); }
.status-dot.connecting { background: var(--yellow); }
.status-text {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
