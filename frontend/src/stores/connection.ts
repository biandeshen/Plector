import { defineStore } from 'pinia'
import { ref, markRaw } from 'vue'

export const useConnectionStore = defineStore('connection', () => {
  const status = ref<'connecting' | 'connected' | 'disconnected'>('disconnected')
  const ws = ref<WebSocket | null>(null)

  function getWsUrl(): string {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${location.host}/ws`
  }

  function connect(onMessage: (data: unknown) => void): void {
    if (ws.value) {
      ws.value.close()
    }

    status.value = 'connecting'
    const socket = new WebSocket(getWsUrl())

    socket.onopen = () => {
      status.value = 'connected'
    }

    socket.onclose = () => {
      status.value = 'disconnected'
      ws.value = null
      // 3 秒后自动重连
      setTimeout(() => {
        if (status.value === 'disconnected') {
          connect(onMessage)
        }
      }, 3000)
    }

    socket.onerror = () => {
      status.value = 'disconnected'
    }

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch {
        // ignore parse errors
      }
    }

    ws.value = markRaw(socket)
  }

  function disconnect(): void {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    status.value = 'disconnected'
  }

  function reconnect(onMessage: (data: unknown) => void): void {
    disconnect()
    // 短暂延迟后重连
    setTimeout(() => connect(onMessage), 100)
  }

  function send(message: { content: string; session_id: string | null }): void {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
    }
  }

  return {
    status,
    connect,
    disconnect,
    reconnect,
    send,
  }
})
