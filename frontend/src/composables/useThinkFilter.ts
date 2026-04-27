/**
 * Think tag 过滤 - 移植自 chat.html filterThink() + cleanThinkingText() + filterToolContent()
 */

const THINK_START = '\uFE4F\uFE5F'
const THINK_END = '\uFE5F'

export function filterThink(content: string): string {
  if (!content) return ''
  return content
    // 自定义分隔符 ﹏﹟...﹟
    .replace(new RegExp(THINK_START + '[\\s\\S]*?' + THINK_END, 'g'), '')
    .replace(new RegExp(THINK_START, 'g'), '')
    .replace(new RegExp(THINK_END, 'g'), '')
    // <think>...</think>
    .replace(/<think>[\s\S]*?<\/think>/gi, '')
    .replace(/<think>[\s\S]*/gi, '')
    .replace(/<\/think>/gi, '')
    // <thinking>...</thinking>
    .replace(/<thinking>[\s\S]*?<\/thinking>/gi, '')
    .replace(/<thinking>[\s\S]*/gi, '')
    .replace(/<\/thinking>/gi, '')
    // <tool_call>...</tool_call>
    .replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, '')
    // 【工具】...【工具结果】
    .replace(/【工具】[\s\S]*?【工具结果】/gi, '')
    // 🔧 工具名... 完成/成功/失败/错误
    .replace(/🔧[\s\S]*?(?:完成|成功|失败|错误)/gi, '')
    // 清理多余空行
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function cleanThinkingText(text: string): string {
  if (!text) return ''
  let cleaned = text
    .replace(/<\/?think>/gi, '')
    .replace(/<\/?thinking>/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  // 去重：如果前半段和后半段内容相同，只保留一份
  if (cleaned.length > 20) {
    const half = Math.floor(cleaned.length / 2)
    const first = cleaned.substring(0, half).trim()
    const second = cleaned.substring(half).trim()
    if (first === second) {
      cleaned = first
    }
  }
  return cleaned
}

export function filterToolContent(content: string, toolResults: string[]): string {
  if (!content) return ''
  let result = content

  for (const toolResult of toolResults) {
    if (toolResult) {
      const shortResult = toolResult.substring(0, 100)
      if (shortResult && result.includes(shortResult)) {
        result = result.replace(toolResult, '')
      }
      result = result.replace(
        /(?:已读取|已写入|已搜索|已执行|成功|失败|错误):[\s\S]*?(?=\n|$)/gi,
        '',
      )
    }
  }

  result = result
    .replace(/^Tool:.*$/gim, '')
    .replace(/^Arguments:[\s\S]*?$/gim, '')
    .replace(/^Result:[\s\S]*?$/gim, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  return result
}
