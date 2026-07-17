import request from './request'
import type { Envelope, Conversation } from '@/types'

/** 获取会话列表 */
export function listConversations(): Promise<Envelope<Conversation[]>> {
  return request.get('/qa/conversations')
}

/** 获取单个会话详情（含历史消息） */
export function getConversation(id: number): Promise<Envelope<Conversation>> {
  return request.get(`/qa/conversations/${id}`)
}

/** 删除会话 */
export function deleteConversation(id: number): Promise<Envelope<null>> {
  return request.delete(`/qa/conversations/${id}`)
}
