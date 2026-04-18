<template>
  <div class="tool-summary">
    <div class="tool-summary-header" @click="togglePanel">
      <span class="tool-summary-arrow" :class="{ expanded: isPanelExpanded }">&#9654;</span>
      <span class="tool-summary-count">
        <strong>{{ tools.length }}</strong> 个工具调用，<strong>{{ processMessageCount }}</strong> 条过程消息
        <template v-if="isStreaming && doneCount < tools.length">
          <span class="tool-summary-progress">({{ doneCount }}/{{ tools.length }} 完成)</span>
        </template>
      </span>
    </div>
    <div v-show="isPanelExpanded" class="tool-summary-details">
      <ToolCallCard
        v-for="(tool, i) in tools"
        :key="tool.toolId"
        :tool="tool"
        :index="i"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolCall } from '@/types'
import ToolCallCard from './ToolCallCard.vue'

const props = defineProps<{
  tools: ToolCall[]
  isStreaming?: boolean
}>()

const isPanelExpanded = ref(false)

const doneCount = computed(() =>
  props.tools.filter((t) => t.status === 'done').length,
)

const processMessageCount = computed(() =>
  props.tools.filter((t) => t.thinking && t.thinking.trim().length > 0).length,
)

function togglePanel() {
  isPanelExpanded.value = !isPanelExpanded.value
}
</script>

<style scoped>
.tool-summary {
  margin-bottom: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
}
.tool-summary-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  transition: background var(--transition-fast);
}
.tool-summary-header:hover { background: rgba(255,255,255,0.05); }
.tool-summary-arrow {
  font-size: 10px;
  color: var(--text-muted);
  transition: transform 0.2s;
  display: inline-block;
}
.tool-summary-arrow.expanded { transform: rotate(90deg); }
.tool-summary-count {
  font-size: 13px;
  color: var(--text-muted);
}
.tool-summary-count strong { color: var(--accent); }
.tool-summary-progress {
  color: var(--text-muted);
  font-size: 12px;
  margin-left: 4px;
}
.tool-summary-details {
  max-height: 300px;
  overflow-y: auto;
}
</style>
