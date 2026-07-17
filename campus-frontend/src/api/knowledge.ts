import request from './request'
import type { R, CampusDocument } from '@/types'

// ========== 文档管理（Python 后端） ==========

export interface DocumentListParams {
  page?: number
  size?: number
  q?: string
}

export interface DocumentListResult {
  items: CampusDocument[]
  total: number
}

/** 文档列表（分页 + 搜索） */
export function listDocuments(params: DocumentListParams): Promise<R<DocumentListResult>> {
  return request.get('/knowledge', { params })
}

/** 获取文档详情 */
export function getDocument(id: number): Promise<R<CampusDocument>> {
  return request.get(`/knowledge/${id}`)
}

/** 上传文档（FormData） */
export function uploadDocument(form: FormData): Promise<R<CampusDocument>> {
  return request.post('/knowledge', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 更新文档元数据 */
export function updateDocument(id: number, data: { title: string; category: string; source_url?: string; published_at?: string }): Promise<R<CampusDocument>> {
  return request.patch(`/knowledge/${id}`, data)
}

/** 删除文档 */
export function deleteDocument(id: number): Promise<R<void>> {
  return request.delete(`/knowledge/${id}`)
}

/** 重新索引文档 */
export function reindexDocument(id: number): Promise<R<void>> {
  return request.post(`/knowledge/${id}/reindex`)
}
