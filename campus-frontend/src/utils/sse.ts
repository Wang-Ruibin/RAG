/**
 * SSE 流式解码器 —— 解析 Python 后端 Server-Sent Events
 *
 * 协议格式：
 *   event: start
 *   data: {"conversation_id": 42}
 *
 *   event: delta
 *   data: {"text": "河海"}
 *
 *   event: done
 *   data: {}
 */
export interface SSEEvent {
  event: string
  data: Record<string, unknown>
}

class SSEDecoder {
  private buffer = ''

  /** 压入文本块，返回解析出的完整事件 */
  push(text: string): SSEEvent[] {
    this.buffer += text.replace(/\r\n/g, '\n')
    const events: SSEEvent[] = []
    let boundary = this.buffer.indexOf('\n\n')

    while (boundary >= 0) {
      const block = this.buffer.slice(0, boundary)
      this.buffer = this.buffer.slice(boundary + 2)

      const lines = block.split('\n')
      const event = lines.find((l) => l.startsWith('event:'))?.slice(6).trim() || 'message'
      const data = lines
        .filter((l) => l.startsWith('data:'))
        .map((l) => l.slice(5).trimStart())
        .join('\n')

      if (data) {
        try {
          events.push({ event, data: JSON.parse(data) as Record<string, unknown> })
        } catch {
          // 跳过非 JSON 行
        }
      }

      boundary = this.buffer.indexOf('\n\n')
    }

    return events
  }

  reset() {
    this.buffer = ''
  }
}

/**
 * 发起流式聊天请求
 * @param question      用户问题
 * @param conversationId 会话 ID（null = 新会话）
 * @param signal        AbortController.signal 用于取消
 * @param onEvent       事件回调
 */
export async function streamChat(
  question: string,
  conversationId: number | null,
  signal: AbortSignal,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const token = localStorage.getItem('campus-token')
  const response = await fetch('/qa/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, conversation_id: conversationId }),
    signal,
  })

  if (!response.ok || !response.body) {
    const payload = (await response.json().catch(() => null)) as { message?: string } | null
    throw new Error(payload?.message || '无法建立流式连接')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const parser = new SSEDecoder()
  let completed = false
  let serverError = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    for (const event of parser.push(decoder.decode(value, { stream: true }))) {
      onEvent(event)
      if (event.event === 'done') completed = true
      if (event.event === 'error') serverError = String(event.data.message || '回答生成失败')
    }
  }

  // 流结束后统一处理错误
  if (serverError) throw new Error(serverError)
  if (!completed) throw new Error('连接意外中断，请重试')
}
