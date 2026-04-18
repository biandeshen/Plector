export interface Conversation {
  id: string
  title: string
  time: string
  createdAt?: string
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  toolCalls: ToolCall[]
}

export interface ToolCall {
  toolId: string
  name: string
  status: 'running' | 'done' | 'error'
  startTime: number
  elapsed: number
  arguments: string
  result: string
  thinking: string
  isExpanded: boolean
}

export interface StreamingState {
  buffer: string
  toolCalls: Map<string, ToolCall>
  isThinking: boolean
  isFinalizing: boolean
}
