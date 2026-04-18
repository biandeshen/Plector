import { onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useConnectionStore } from '@/stores/connection'

export function useWebSocket(): void {
  const chatStore = useChatStore()
  const connectionStore = useConnectionStore()

  onMounted(() => {
    connectionStore.connect(chatStore.routeEvent)
    chatStore.loadConversations()
  })

  onUnmounted(() => {
    connectionStore.disconnect()
  })
}
