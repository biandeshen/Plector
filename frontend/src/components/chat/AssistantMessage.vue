<template>
  <div class="message assistant">
    <div class="msg-avatar">&#129438;</div>
    <div class="msg-content">
      <div class="bubble">
        <ToolSummaryPanel
          v-if="toolCalls.length > 0"
          :tools="toolCalls"
          :is-streaming="isStreaming"
        />
        <MarkdownContent
          v-if="displayContent"
          :content="displayContent"
          :is-streaming="isStreaming"
        />
        <StreamingCursor v-if="isStreaming && !isFinalizing" />
      </div>
      <button class="copy-btn" @click="copyMessage">复制</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Message, ToolCall } from '@/types'
import { filterToolContent } from '@/composables/useThinkFilter'
import ToolSummaryPanel from '@/components/tools/ToolSummaryPanel.vue'
import MarkdownContent from './MarkdownContent.vue'
import StreamingCursor from './StreamingCursor.vue'

const props = defineProps<{
  message?: Message
  streamBuffer?: string
  streamToolCalls?: ToolCall[]
  isStreaming?: boolean
  isFinalizing?: boolean
}>()

const toolCalls = computed<ToolCall[]>(() => {
  if (props.streamToolCalls) return props.streamToolCalls
  return props.message?.toolCalls || []
})

const displayContent = computed(() => {
  let content = ''
  if (props.isStreaming) {
    content = props.streamBuffer || ''
  } else {
    content = props.message?.content || ''
  }
  // 过滤掉工具结果在文本中的重复
  if (toolCalls.value.length > 0) {
    const results = toolCalls.value.map((t) => t.result).filter(Boolean)
    content = filterToolContent(content, results)
  }
  return content
})

const copyBtnText = ref('复制')

function copyMessage() {
  const text = props.message?.content || props.streamBuffer || ''
  navigator.clipboard.writeText(text).then(() => {
    copyBtnText.value = '已复制 ✓'
    setTimeout(() => { copyBtnText.value = '复制' }, 2000)
  })
}
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
  animation: fadeIn 0.3s ease;
}
.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  background: var(--surface);
  border: 1px solid var(--border);
}
.msg-content {
  flex: 1;
  min-width: 0;
  position: relative;
}
.bubble {
  padding: 10px 14px;
  border-radius: 10px 10px 3px 10px;
  font-size: 14px;
  line-height: 1.6;
  background: var(--surface);
  border: 1px solid var(--border);
}
.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}
.msg-content:hover .copy-btn { opacity: 1; }
.copy-btn:hover {
  background: var(--surface);
  color: var(--text);
}
</style>
