<template>
  <div
    class="conv-item"
    :class="{ active: isActive }"
    @click="$emit('select', conversation.id)"
  >
    <div v-if="isRenaming" class="rename-wrapper" @click.stop>
      <input
        ref="renameInputRef"
        class="rename-input"
        :value="renameValue"
        @input="renameValue = ($event.target as HTMLInputElement).value"
        @keydown.enter="finishRename"
        @blur="finishRename"
      />
    </div>
    <template v-else>
      <span class="conv-title" @dblclick.stop="startRename">{{ conversation.title }}</span>
      <span class="conv-time">{{ conversation.time }}</span>
      <button class="delete-btn" @click.stop="$emit('delete', conversation.id)">&#10005;</button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import type { Conversation } from '@/types'

const props = defineProps<{
  conversation: Conversation
  isActive: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  delete: [id: string]
  rename: [id: string, title: string]
}>()

const isRenaming = ref(false)
const renameValue = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)

function startRename() {
  renameValue.value = props.conversation.title
  isRenaming.value = true
  nextTick(() => {
    renameInputRef.value?.focus()
    renameInputRef.value?.select()
  })
}

function finishRename() {
  const newTitle = renameValue.value.trim()
  isRenaming.value = false
  if (newTitle && newTitle !== props.conversation.title) {
    emit('rename', props.conversation.id, newTitle)
  }
}
</script>

<style scoped>
.conv-item {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  color: var(--text);
  transition: background 0.15s;
}
.conv-item:hover { background: var(--surface-2); }
.conv-item.active { background: var(--accent-dim); border-left: 3px solid var(--accent); }
.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 8px;
  flex-shrink: 0;
}
.delete-btn {
  opacity: 0;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
}
.conv-item:hover .delete-btn { opacity: 1; }
.delete-btn:hover { color: var(--red); }
.rename-wrapper { flex: 1; }
.rename-input {
  background: var(--bg);
  border: 1px solid var(--accent);
  border-radius: 4px;
  padding: 4px 8px;
  color: var(--text);
  font-size: 13px;
  width: 100%;
  outline: none;
}
</style>
