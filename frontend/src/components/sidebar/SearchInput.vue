<template>
  <input
    class="search-input"
    type="text"
    :value="modelValue"
    placeholder="搜索对话..."
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<script setup lang="ts">
defineProps<{ modelValue: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<style scoped>
.search-input {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text);
  font-size: 13px;
  outline: none;
  margin-bottom: 8px;
}
.search-input:focus { border-color: var(--accent); }
.search-input::placeholder { color: var(--text-weak); }
</style>
