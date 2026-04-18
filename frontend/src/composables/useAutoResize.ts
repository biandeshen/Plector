import { type Ref, onMounted, onUnmounted, watch } from 'vue'

export function useAutoResize(
  textareaRef: Ref<HTMLTextAreaElement | null>,
  minHeight = 40,
  maxHeight = 160,
): void {
  function resize() {
    const el = textareaRef.value
    if (!el) return
    el.style.height = 'auto'
    const newHeight = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight)
    el.style.height = newHeight + 'px'
  }

  onMounted(() => {
    const el = textareaRef.value
    if (el) {
      el.addEventListener('input', resize)
      resize()
    }
  })

  onUnmounted(() => {
    const el = textareaRef.value
    if (el) {
      el.removeEventListener('input', resize)
    }
  })

  watch(textareaRef, (newEl, oldEl) => {
    if (oldEl) oldEl.removeEventListener('input', resize)
    if (newEl) {
      newEl.addEventListener('input', resize)
      resize()
    }
  })
}
