import { Marked } from 'marked'
import hljs from 'highlight.js'

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

let markedInstance: Marked | null = null

function getMarked(): Marked {
  if (markedInstance) return markedInstance

  markedInstance = new Marked({
    breaks: true,
    gfm: true,
  })

  markedInstance.use({
    renderer: {
      code(this: unknown, code: string, infostring: string | undefined): string | false {
        const lang = infostring?.split(/\s/)[0] || ''
        const language = lang && hljs.getLanguage(lang) ? lang : ''
        let highlighted: string
        try {
          highlighted = language
            ? hljs.highlight(code, { language }).value
            : hljs.highlightAuto(code).value
        } catch {
          highlighted = escapeHtml(code)
        }
        const langLabel = language || 'text'
        const escapedCode = escapeHtml(code)
        return `<div class="code-block">
  <div class="code-block-header">
    <span class="code-block-lang">${langLabel}</span>
    <button class="code-copy-btn" data-code="${escapedCode}">复制</button>
  </div>
  <pre><code class="hljs${language ? ` language-${language}` : ''}">${highlighted}</code></pre>
</div>`
      },
    },
  })

  return markedInstance
}

export function renderMarkdown(content: string): string {
  if (!content) return ''
  const marked = getMarked()
  return marked.parse(content) as string
}

export function setupCodeCopyHandler(container: HTMLElement): void {
  container.addEventListener('click', (e: Event) => {
    const target = e.target as HTMLElement
    if (!target.classList.contains('code-copy-btn')) return

    const code = target.getAttribute('data-code')
    if (!code) return

    navigator.clipboard.writeText(code).then(() => {
      target.textContent = '已复制 ✓'
      target.classList.add('copied')
      setTimeout(() => {
        target.textContent = '复制'
        target.classList.remove('copied')
      }, 2000)
    })
  })
}
