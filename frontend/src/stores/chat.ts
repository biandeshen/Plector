import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Conversation, Message, ToolCall } from '@/types'
import { filterThink } from '@/composables/useThinkFilter'
import {
  fetchConversations,
  fetchMessages,
  fetchToolCalls,
  createConversation as apiCreateConversation,
  renameConversation as apiRenameConversation,
  deleteConversation as apiDeleteConversation,
  processConversationData,
} from '@/services/api'
import { useConnectionStore } from './connection'

export const useChatStore = defineStore('chat', () => {
  // ======= State =======
  const conversations = ref<Conversation[]>([])
  const currentConversationId = ref<string | null>(null)
  const messagesCache = ref<Record<string, Message[]>>({})
  const searchQuery = ref('')

  // Streaming state
  const isStreaming = ref(false)
  const streamBuffer = ref('')
  const streamToolCalls = ref<Map<string, ToolCall>>(new Map())
  const streamIsThinking = ref(false)
  const streamIsFinalizing = ref(false)

  // ======= Getters =======
  const currentMessages = computed(() => {
    if (!currentConversationId.value) return []
    return messagesCache.value[currentConversationId.value] || []
  })

  const filteredConversations = computed(() => {
    if (!searchQuery.value) return conversations.value
    const q = searchQuery.value.toLowerCase()
    return conversations.value.filter((c) =>
      c.title.toLowerCase().includes(q),
    )
  })

  const groupedConversations = computed(() => {
    const groups: Record<string, Conversation[]> = {
      '今天': [],
      '昨天': [],
      '本周': [],
      '更早': [],
    }

    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today.getTime() - 86400000)
    const weekAgo = new Date(today.getTime() - 7 * 86400000)

    for (const conv of filteredConversations.value) {
      const convDate = new Date(conv.time)
      if (convDate >= today) {
        groups['今天'].push(conv)
      } else if (convDate >= yesterday) {
        groups['昨天'].push(conv)
      } else if (convDate >= weekAgo) {
        groups['本周'].push(conv)
      } else {
        groups['更早'].push(conv)
      }
    }

    return groups
  })

  const orderedToolCalls = computed(() => {
    return Array.from(streamToolCalls.value.values())
  })

  const lastUserMessage = computed<Message | null>(() => {
    const msgs = currentMessages.value
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') return msgs[i]
    }
    return null
  })

  const doneToolCallCount = computed(() => {
    let count = 0
    for (const tc of streamToolCalls.value.values()) {
      if (tc.status === 'done') count++
    }
    return count
  })

  // ======= Actions =======

  async function loadConversations(): Promise<void> {
    try {
      conversations.value = await fetchConversations()
    } catch (e) {
      console.error('加载对话列表失败:', e)
    }
  }

  async function selectConversation(id: string): Promise<void> {
    currentConversationId.value = id
    resetStreaming()

    // 如果已缓存，直接使用
    if (messagesCache.value[id]) return

    try {
      const [msgsData, toolsData] = await Promise.all([
        fetchMessages(id),
        fetchToolCalls(id),
      ])
      const messages = processConversationData(msgsData, toolsData)
      messagesCache.value[id] = messages
    } catch (e) {
      console.error('加载对话失败:', e)
    }
  }

  async function createNewConversation(): Promise<string> {
    const sessionId = await apiCreateConversation()
    // 添加到列表顶部
    const d = new Date()
    const time = `${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    conversations.value.unshift({
      id: sessionId,
      title: '新对话',
      time,
    })
    currentConversationId.value = sessionId
    messagesCache.value[sessionId] = []
    return sessionId
  }

  async function renameConversation(id: string, title: string): Promise<void> {
    await apiRenameConversation(id, title)
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.title = title
  }

  async function removeConversation(id: string): Promise<void> {
    await apiDeleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    delete messagesCache.value[id]
    if (currentConversationId.value === id) {
      currentConversationId.value = null
    }
  }

  function newChat(): void {
    currentConversationId.value = null
    resetStreaming()
  }

  // ======= Streaming Actions =======

  function initStreaming(): void {
    isStreaming.value = true
    streamBuffer.value = ''
    streamToolCalls.value = new Map()
    streamIsThinking.value = true
    streamIsFinalizing.value = false
  }

  function appendChunk(content: string): void {
    const filtered = filterThink(content)
    if (!filtered) return
    if (!isStreaming.value) initStreaming()
    streamBuffer.value += filtered
    streamIsThinking.value = false
  }

  function addToolCall(event: {
    tool?: string
    toolId: string
    arguments?: string
    thinking?: string
  }): void {
    if (!event.toolId) return
    if (!isStreaming.value) initStreaming()

    if (!streamToolCalls.value.has(event.toolId)) {
      const tc: ToolCall = {
        toolId: event.toolId,
        name: event.tool || 'tool',
        status: 'running',
        startTime: Date.now(),
        elapsed: 0,
        arguments: event.arguments || '',
        result: '',
        thinking: event.thinking || '',
        isExpanded: false,
      }
      streamToolCalls.value.set(event.toolId, tc)
    }
    streamIsThinking.value = false
  }

  function updateToolCall(event: {
    toolId: string
    result?: string
    error?: string
    thinking?: string
  }): void {
    const toolId = event.toolId
    if (!toolId) return
    const tc = streamToolCalls.value.get(toolId)
    if (tc) {
      tc.status = 'done'
      tc.elapsed = parseFloat(((Date.now() - tc.startTime) / 1000).toFixed(1))
      tc.result = event.result || event.error || ''
      if (!tc.thinking && event.thinking) {
        tc.thinking = event.thinking
      }
    }
  }

  function startToolCallBatch(_count: number): void {
    // 可用于 UI 进度指示
  }

  function finalizeMessage(content?: string): void {
    if (streamIsFinalizing.value) return
    streamIsFinalizing.value = true

    let finalContent = streamBuffer.value
    if (content) {
      const filtered = filterThink(content)
      if (filtered && !finalContent.includes(filtered)) {
        finalContent = filtered
      }
    }

    if (!currentConversationId.value) {
      resetStreaming()
      return
    }

    // 创建最终消息
    const toolCalls = Array.from(streamToolCalls.value.values())
    if (finalContent.trim() || toolCalls.length > 0) {
      const msg: Message = {
        id: Date.now(),
        role: 'assistant',
        content: finalContent,
        toolCalls,
      }
      if (!messagesCache.value[currentConversationId.value]) {
        messagesCache.value[currentConversationId.value] = []
      }
      messagesCache.value[currentConversationId.value].push(msg)
    }

    resetStreaming()
    // 刷新对话列表标题
    loadConversations()
  }

  function handleBatchResponse(event: {
    content?: string
    tool_calls?: unknown[]
  }): void {
    if (event.content) {
      const filtered = filterThink(event.content)
      if (filtered) {
        if (!isStreaming.value) initStreaming()
        streamBuffer.value = filtered
      }
    }
    finalizeMessage(event.content)
  }

  function handleError(event: { content?: string; error?: string }): void {
    const errorMsg = event.error || event.content || '执行失败'
    if (!isStreaming.value) initStreaming()
    streamBuffer.value = `**错误**: ${errorMsg}`
    finalizeMessage()
  }

  function stopGeneration(): void {
    const connectionStore = useConnectionStore()
    // 保留已有内容作为消息
    finalizeMessage()
    connectionStore.reconnect(routeEvent)
  }

  function addUserMessage(content: string): void {
    if (!currentConversationId.value) return
    if (!messagesCache.value[currentConversationId.value]) {
      messagesCache.value[currentConversationId.value] = []
    }
    messagesCache.value[currentConversationId.value].push({
      id: Date.now(),
      role: 'user',
      content,
      toolCalls: [],
    })
  }

  function regenerateLastResponse(): void {
    if (!currentConversationId.value) return
    const msgs = messagesCache.value[currentConversationId.value]
    if (!msgs || msgs.length === 0) return

    // Find and remove the last assistant message
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant') {
        msgs.splice(i, 1)
        break
      }
      // Stop if we hit another user message
      if (msgs[i].role === 'user') break
    }

    // Find the last user message
    const lastUser = lastUserMessage.value
    if (!lastUser) return

    // Re-send the user message
    const connectionStore = useConnectionStore()
    initStreaming()
    connectionStore.send({
      content: lastUser.content,
      session_id: currentConversationId.value,
    })
  }

  // ======= WebSocket 事件路由 =======

  function routeEvent(data: unknown): void {
    const event = data as Record<string, unknown>
    const eventType = event.type as string
    switch (eventType) {
      case 'chunk':
        appendChunk(event.content as string)
        break
      case 'toolExecuting':
      case 'tool_call_start':
        if (event.toolId) {
          addToolCall({
            tool: event.tool as string | undefined,
            toolId: event.toolId as string,
            arguments: event.arguments as string | undefined,
            thinking: event.thinking as string | undefined,
          })
        } else if (eventType === 'tool_call_start') {
          startToolCallBatch(event.count as number)
        }
        break
      case 'toolDone':
        updateToolCall({
          toolId: event.toolId as string,
          result: event.result as string | undefined,
          error: event.error as string | undefined,
          thinking: event.thinking as string | undefined,
        })
        break
      case 'done':
        finalizeMessage(event.content as string)
        break
      case 'response':
        handleBatchResponse({
          content: event.content as string | undefined,
          tool_calls: event.tool_calls as unknown[] | undefined,
        })
        break
      case 'error':
        handleError({
          content: event.content as string | undefined,
          error: event.error as string | undefined,
        })
        break
    }
  }

  // ======= Internal =======

  function resetStreaming(): void {
    isStreaming.value = false
    streamBuffer.value = ''
    streamToolCalls.value = new Map()
    streamIsThinking.value = false
    streamIsFinalizing.value = false
  }

  return {
    // State
    conversations,
    currentConversationId,
    messagesCache,
    searchQuery,
    isStreaming,
    streamBuffer,
    streamToolCalls,
    streamIsThinking,
    streamIsFinalizing,
    // Getters
    currentMessages,
    filteredConversations,
    groupedConversations,
    orderedToolCalls,
    doneToolCallCount,
    lastUserMessage,
    // Actions
    loadConversations,
    selectConversation,
    createNewConversation,
    renameConversation,
    removeConversation,
    newChat,
    initStreaming,
    appendChunk,
    addToolCall,
    updateToolCall,
    startToolCallBatch,
    finalizeMessage,
    handleBatchResponse,
    handleError,
    stopGeneration,
    addUserMessage,
    regenerateLastResponse,
    routeEvent,
  }
})
