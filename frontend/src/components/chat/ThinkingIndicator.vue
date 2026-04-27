<template>
  <div class="thinking">
    <div class="thinking-dots">
      <span></span><span></span><span></span>
    </div>
    <span>思考中...</span>
  </div>
</template>

<style scoped>
.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
  padding: 8px 0;
}
.thinking-dots span {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--text-weak);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}
.thinking-dots span:nth-child(1) { animation-delay: -0.32s; }
.thinking-dots span:nth-child(2) { animation-delay: -0.16s; }
.thinking-dots span:nth-child(3) { animation-delay: 0s; }
</style>
