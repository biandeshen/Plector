<template>
  <div class="welcome">
    <h1 class="title">Plector</h1>
    <p class="subtitle">你的 AI Agent 助手</p>

    <div class="suggestions">
      <button
        class="suggestion-card"
        v-for="s in suggestions"
        :key="s.text"
        @click="$emit('select', s.text)"
      >
        <span class="suggestion-icon">{{ s.icon }}</span>
        <span class="suggestion-text">{{ s.text }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits<{
  select: [text: string]
}>()

const suggestions: { text: string; icon: string }[] = [
  { text: '帮我写一个 Python 脚本', icon: '📝' },
  { text: '解释这段代码做了什么', icon: '🔍' },
  { text: '搜索最新的 AI 新闻', icon: '🌐' },
  { text: '分析这个项目的架构', icon: '🏗️' },
  { text: '帮我检查系统健康状态', icon: '💚' },
  { text: '继续之前的任务', icon: '▶️' },
]
</script>

<style scoped>
.welcome {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.title {
  font-size: 32px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 8px 0;
}
.subtitle {
  font-size: 16px;
  color: var(--text-muted);
  margin: 0 0 40px 0;
}
.suggestions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-width: 600px;
  width: 100%;
}
.suggestion-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  color: var(--text);
  font-size: 14px;
}
.suggestion-card:hover {
  background: var(--bg-tertiary);
  border-color: var(--accent);
  transform: translateY(-1px);
}
.suggestion-card:active {
  transform: translateY(0);
}
.suggestion-icon {
  font-size: 18px;
  flex-shrink: 0;
}
.suggestion-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
