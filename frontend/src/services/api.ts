import type { Conversation, Message, ToolCall } from '@/types'

const BASE = ''

interface ConversationsResponse {
  conversations: Array<{
    session_id: string
    title: string
    created_at: string
  }>
}

interface MessagesResponse {
  session_id: string
  messages: Array<{
    id: number
    role: string
    content: string
  }>
}

interface ToolCallsResponse {
  session_id: string
  tool_calls: Array<{
    id: number
    tool_name: string
    arguments: string
    result: string
    thinking: string
    message_index: number
    elapsed: number | string
  }>
}

interface CreateConversationResponse {
  session_id: string
}

export async function fetchConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/api/conversations`)
  const data: ConversationsResponse = await res.json()
  return (data.conversations || []).map((c) => {
    const d = new Date(c.created_at)
    const time = `${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    return {
      id: c.session_id,
      title: c.title ? (c.title.length > 30 ? c.title.substring(0, 30) + '...' : c.title) : '新对话',
      time,
      createdAt: c.created_at,
    }
  })
}

export async function fetchMessages(sessionId: string): Promise<MessagesResponse> {
  const res = await fetch(`${BASE}/api/conversations/${sessionId}`)
  return res.json()
}

export async function fetchToolCalls(sessionId: string): Promise<ToolCallsResponse> {
  const res = await fetch(`${BASE}/api/tool-calls/${sessionId}`)
  return res.json()
}

export async function createConversation(): Promise<string> {
  const res = await fetch(`${BASE}/api/conversations`, { method: 'POST' })
  const data: CreateConversationResponse = await res.json()
  return data.session_id
}

export async function renameConversation(sessionId: string, title: string): Promise<void> {
  await fetch(`${BASE}/api/conversations/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
}

export async function deleteConversation(sessionId: string): Promise<void> {
  await fetch(`${BASE}/api/conversations/${sessionId}`, { method: 'DELETE' })
}

export function parseToolCallsFromApi(
  rawTools: ToolCallsResponse['tool_calls'],
): Map<number, ToolCall[]> {
  const grouped = new Map<number, ToolCall[]>()
  for (const t of rawTools) {
    const tc: ToolCall = {
      toolId: `hist-${t.id}`,
      name: t.tool_name,
      status: 'done',
      startTime: 0,
      elapsed: typeof t.elapsed === 'string' ? parseFloat(t.elapsed) : (t.elapsed || 0),
      arguments: t.arguments || '',
      result: t.result || '',
      thinking: t.thinking || '',
      isExpanded: false,
    }
    const idx = t.message_index
    if (!grouped.has(idx)) {
      grouped.set(idx, [])
    }
    grouped.get(idx)!.push(tc)
  }
  return grouped
}

export function processConversationData(
  messagesData: MessagesResponse,
  toolCallsData: ToolCallsResponse,
): Message[] {
  const toolsByIndex = parseToolCallsFromApi(toolCallsData.tool_calls || [])
  const messages: Message[] = []
  const rawMsgs = messagesData.messages || []

  let accContent = ''
  let accIds: number[] = []

  for (const msg of rawMsgs) {
    if (msg.role === 'user') {
      // 先输出积累的 assistant 内容
      if (accContent || accIds.length > 0) {
        const tools: ToolCall[] = []
        for (const id of accIds) {
          const matched = toolsByIndex.get(id)
          if (matched) {
            tools.push(...matched)
            toolsByIndex.delete(id)
          }
        }
        if (accContent.trim()) {
          messages.push({
            id: accIds[0] || 0,
            role: 'assistant',
            content: accContent,
            toolCalls: tools,
          })
        }
        accContent = ''
        accIds = []
      }
      // 跳过 [新对话] 占位消息
      if (msg.content === '[新对话]') continue
      messages.push({
        id: msg.id,
        role: 'user',
        content: msg.content,
        toolCalls: [],
      })
    } else if (msg.role === 'assistant') {
      accContent += (accContent ? '\n' : '') + msg.content
      accIds.push(msg.id)
    }
  }

  // 输出最后的 assistant 消息
  if (accContent || accIds.length > 0) {
    const tools: ToolCall[] = []
    for (const id of accIds) {
      const matched = toolsByIndex.get(id)
      if (matched) {
        tools.push(...matched)
        toolsByIndex.delete(id)
      }
    }
    // Fallback: 未匹配的 tool_calls 附加到最后一条消息
    if (toolsByIndex.size > 0 && tools.length === 0) {
      for (const [, remaining] of toolsByIndex) {
        tools.push(...remaining)
      }
    }
    if (accContent.trim()) {
      messages.push({
        id: accIds[0] || 0,
        role: 'assistant',
        content: accContent,
        toolCalls: tools,
      })
    }
  }

  return messages
}
