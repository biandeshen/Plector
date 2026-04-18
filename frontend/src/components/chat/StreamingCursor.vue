<template>
  <span class="streaming-cursor"></span>
</template>

<style scoped>
.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--accent);
  animation: blink 1s infinite;
  vertical-align: text-bottom;
  margin-left: 2px;
}
</style>
