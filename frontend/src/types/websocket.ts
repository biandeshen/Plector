export interface WsChunkEvent {
  type: 'chunk'
  content: string
}

export interface WsToolExecutingEvent {
  type: 'toolExecuting'
  tool: string
  toolId: string
  arguments: string
  thinking: string
}

export interface WsToolDoneEvent {
  type: 'toolDone'
  tool: string
  toolId: string
  result: string
  error?: string
  thinking?: string
}

export interface WsToolCallStartEvent {
  type: 'tool_call_start'
  count: number
}

export interface WsDoneEvent {
  type: 'done'
  content: string
}

export interface WsResponseEvent {
  type: 'response'
  content: string
  tool_calls?: Array<{ name: string; function?: { name: string } }>
}

export interface WsErrorEvent {
  type: 'error'
  content?: string
  error?: string
}

export type WsEvent =
  | WsChunkEvent
  | WsToolExecutingEvent
  | WsToolDoneEvent
  | WsToolCallStartEvent
  | WsDoneEvent
  | WsResponseEvent
  | WsErrorEvent

export interface WsOutgoingMessage {
  content: string
  session_id: string | null
}
