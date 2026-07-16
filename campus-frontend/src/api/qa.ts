import request from './request'
import type { R } from '@/types'

export function askQuestion(question: string): Promise<R<{ question: string; answer: string; sources: any[] }>> {
  return request.post('/qa/ask', { question })
}
