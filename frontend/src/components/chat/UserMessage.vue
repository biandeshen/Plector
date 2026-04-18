<template>
  <div class="message user">
    <div class="msg-content">
      <div class="bubble">{{ content }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ content: string }>()
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
  animation: fadeIn 0.3s ease;
  margin-left: auto;
  flex-direction: row-reverse;
}
.msg-content { flex: 1; min-width: 0; }
.bubble {
  padding: 10px 14px;
  border-radius: 10px 10px 3px 10px;
  font-size: 14px;
  line-height: 1.6;
  background: var(--btn);
  color: white;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
