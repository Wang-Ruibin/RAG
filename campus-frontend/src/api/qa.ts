import request from './request'
import type { Envelope, Conversation, AnswerKnowledgeTask, AnswerCorrection, AdminAnswerCorrection, QaConversationItem } from '@/types'

/** 获取会话列表，支持按标题模糊搜索 */
export function listConversations(q?: string): Promise<Envelope<Conversation[]>> {
  return request.get('/qa/conversations', q ? { params: { q } } : {})
}

/** 获取单个会话详情（含历史消息） */
export function getConversation(id: number): Promise<Envelope<Conversation>> {
  return request.get(`/qa/conversations/${id}`)
}

/** 重命名会话 */
export function renameConversation(id: number, title: string): Promise<Envelope<Conversation>> {
  return request.patch(`/qa/conversations/${id}`, { title })
}

/** 删除会话 */
export function deleteConversation(id: number): Promise<Envelope<null>> {
  return request.delete(`/qa/conversations/${id}`)
}

// ========== 管理员问答管理 ==========

export interface QaConversationPage {
  items: QaConversationItem[]
  total: number
  page: number
  size: number
}

/** 管理员删除任意会话 */
export function deleteQaConversation(id: number): Promise<Envelope<null>> {
  return request.delete(`/qa/admin/qa-conversations/${id}`)
}

/** 问答管理列表（管理员），支持关键词、用户、日期范围、来源类型、状态筛选 */
export function listQaConversations(params: {
  page?: number
  size?: number
  keyword?: string
  user_id?: number
  user_name?: string
  start_date?: string
  end_date?: string
  answer_origin?: string
  status?: string
}): Promise<Envelope<QaConversationPage>> {
  return request.get('/qa/admin/qa-conversations', { params })
}

// ========== 点赞沉淀 / 点踩纠错 ==========

/** 点赞：把答案沉淀进知识库（进任务队列） */
export function createKnowledgeTask(messageId: number): Promise<Envelope<AnswerKnowledgeTask>> {
  return request.post(`/qa/messages/${messageId}/knowledge-task`)
}

/** 查询某条消息的沉淀任务状态 */
export function getKnowledgeTask(messageId: number): Promise<Envelope<AnswerKnowledgeTask | null>> {
  return request.get(`/qa/messages/${messageId}/knowledge-task`)
}

/** 点踩：提交纠错答案，等待管理员审核 */
export function submitCorrection(messageId: number, correctedAnswer: string): Promise<Envelope<AnswerCorrection>> {
  return request.post(`/qa/messages/${messageId}/correction`, { corrected_answer: correctedAnswer })
}

// ========== 纠错审核（管理员） ==========

export interface CorrectionPage {
  items: AdminAnswerCorrection[]
  total: number
  page: number
  size: number
}

/** 纠错列表（status_filter 可选 PENDING/PROCESSING/APPROVED/REJECTED/FAILED） */
export function listCorrections(params: { page?: number; size?: number; status_filter?: string }): Promise<Envelope<CorrectionPage>> {
  return request.get('/qa/admin/answer-corrections', { params })
}

/** 通过纠错（可修改问题/答案后入库） */
export function approveCorrection(
  id: number,
  data: { question: string; answer: string; source_document_ids?: number[] },
): Promise<Envelope<AdminAnswerCorrection>> {
  return request.post(`/qa/admin/answer-corrections/${id}/approve`, data)
}

/** 拒绝纠错 */
export function rejectCorrection(id: number, reason: string): Promise<Envelope<AdminAnswerCorrection>> {
  return request.post(`/qa/admin/answer-corrections/${id}/reject`, { reason })
}
