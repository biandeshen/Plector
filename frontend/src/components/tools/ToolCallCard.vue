<template>
  <div class="tool-item">
    <div class="tool-item-header" @click="toggleExpand">
      <span class="step-number">{{ index + 1 }}</span>
      <span class="tool-item-name">{{ tool.name }}</span>
      <span class="tool-item-status" :class="tool.status">
        <span v-if="tool.status === 'running'" class="spinner"></span>
        <span v-else-if="tool.status === 'done'" class="check-icon">&#10003;</span>
        <span v-else class="error-icon">&#10007;</span>
        {{ statusLabel }}
      </span>
      <span v-if="tool.elapsed" class="tool-elapsed">{{ tool.elapsed }}s</span>
      <span class="tool-item-toggle" :class="{ expanded: isExpanded }">&#9660;</span>
    </div>
    <div class="tool-detail-content" :class="{ expanded: isExpanded }">
      <div v-if="cleanedThinking" class="tool-section thinking-section">
        <div class="section-label">思考</div>
        <div class="thinking-text">{{ cleanedThinking }}</div>
      </div>
      <div v-if="tool.arguments" class="tool-section args-section">
        <div class="section-label">参数</div>
        <pre class="section-content">{{ formattedArgs }}</pre>
      </div>
      <div v-if="tool.result" class="tool-section result-section">
        <div class="section-label">结果</div>
        <pre class="section-content">{{ truncatedResult }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolCall } from '@/types'
import { cleanThinkingText } from '@/composables/useThinkFilter'

const props = defineProps<{ tool: ToolCall; index: number }>()

const isExpanded = ref(props.tool.isExpanded)

const statusLabel = computed(() => {
  switch (props.tool.status) {
    case 'running': return '执行中'
    case 'done': return '完成'
    case 'error': return '失败'
  }
})

const cleanedThinking = computed(() => cleanThinkingText(props.tool.thinking))

const formattedArgs = computed(() => {
  if (!props.tool.arguments) return ''
  try {
    return JSON.stringify(JSON.parse(props.tool.arguments), null, 2)
  } catch {
    return props.tool.arguments
  }
})

const truncatedResult = computed(() => {
  const r = props.tool.result
  if (!r) return ''
  return r.length > 500 ? r.substring(0, 500) + '...' : r
})

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}
</script>

<style scoped>
.tool-item {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.tool-item:last-child { border-bottom: none; }
.tool-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  background: var(--surface);
  transition: background var(--transition-fast);
}
.tool-item-header:hover { background: rgba(255,255,255,0.03); }
.step-number {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent-dim);
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tool-item-name { color: var(--accent); font-weight: 600; font-size: 13px; }
.tool-item-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}
.tool-item-status.done { background: var(--green-bg); color: var(--green); }
.tool-item-status.running { background: var(--yellow-bg); color: var(--yellow); }
.tool-item-status.error { background: var(--red-bg); color: var(--red); }
.spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 2px solid var(--yellow);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
.check-icon { animation: checkIn 0.3s ease; }
.tool-elapsed {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.tool-item-toggle {
  font-size: 11px;
  color: var(--text-muted);
  transition: transform 0.2s;
}
.tool-item-toggle.expanded { transform: rotate(180deg); }

/* 折叠/展开过渡 */
.tool-detail-content {
  max-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: max-height var(--transition-normal), opacity 0.2s ease;
}
.tool-detail-content.expanded {
  max-height: 600px;
  opacity: 1;
  overflow-y: scroll;
}
.tool-section {
  padding: 8px 12px;
  border-top: 1px solid var(--border);
}
.section-label {
  color: var(--text);
  font-weight: 500;
  margin-bottom: 4px;
  font-size: 12px;
}
.thinking-section {
  background: var(--surface);
}
.thinking-text {
  color: var(--text-muted);
  font-size: 12px;
  font-style: italic;
  line-height: 1.5;
}
.args-section, .result-section {
  background: var(--bg);
}
.section-content {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>
