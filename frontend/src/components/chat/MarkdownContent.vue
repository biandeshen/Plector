<template>
  <div class="markdown-content bubble" ref="containerRef" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUpdated } from 'vue'
import { renderMarkdown, setupCodeCopyHandler } from '@/composables/useMarkdown'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()

const containerRef = ref<HTMLElement | null>(null)

const renderedHtml = computed(() => renderMarkdown(props.content))

onMounted(() => {
  if (containerRef.value) {
    setupCodeCopyHandler(containerRef.value)
  }
})

onUpdated(() => {
  // highlight.js 已在 marked renderer 中处理，无需额外操作
})
</script>
