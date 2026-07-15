export interface SSEEvent {
  event: string
  data: Record<string, unknown>
}

export class SSEDecoder {
  private buffer = ''

  push(text: string): SSEEvent[] {
    this.buffer += text.replace(/\r\n/g, '\n')
    const events: SSEEvent[] = []
    let boundary = this.buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const block = this.buffer.slice(0, boundary)
      this.buffer = this.buffer.slice(boundary + 2)
      const lines = block.split('\n')
      const event = lines.find((line) => line.startsWith('event:'))?.slice(6).trim() || 'message'
      const data = lines
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (data) events.push({ event, data: JSON.parse(data) as Record<string, unknown> })
      boundary = this.buffer.indexOf('\n\n')
    }
    return events
  }
}

export async function streamChat(
  question: string,
  conversationId: number | null,
  signal: AbortSignal,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const token = localStorage.getItem('campusqa_token')
  const response = await fetch('/api/chat/stream', {
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
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    for (const event of parser.push(decoder.decode(value, { stream: true }))) onEvent(event)
  }
}
