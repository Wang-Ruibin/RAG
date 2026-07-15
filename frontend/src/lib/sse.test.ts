import { describe, expect, it } from 'vitest'
import { SSEDecoder } from './sse'

describe('SSEDecoder', () => {
  it('handles events split across network chunks', () => {
    const decoder = new SSEDecoder()
    expect(decoder.push('event: delta\ndata: {"text":"河')).toEqual([])
    expect(decoder.push('海"}\n\nevent: done\ndata: {}\n\n')).toEqual([
      { event: 'delta', data: { text: '河海' } },
      { event: 'done', data: {} },
    ])
  })
})
