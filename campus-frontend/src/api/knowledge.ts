import request from './request'
import type { Envelope, CampusDocument } from '@/types'

// ========== 文档管理（Python 后端） ==========

export interface DocumentListParams {
  page?: number
  size?: number
  q?: string
  category?: string
  status_filter?: CampusDocument['status']
}

export interface DocumentListResult {
  items: CampusDocument[]
  total: number
  page: number
  size: number
}

export interface UploadDocumentResponse {
  document: CampusDocument
  job_id: number
}

export interface ReindexDocumentResponse {
  document_id: number
  job_id: number
}

/** 文档列表（分页 + 搜索） */
export function listDocuments(params: DocumentListParams): Promise<Envelope<DocumentListResult>> {
  const query = {
    page: params.page,
    size: params.size,
    q: params.q || undefined,
    category: params.category || undefined,
    status_filter: params.status_filter || undefined,
  }
  return request.get('/knowledge', { params: query })
}

/** 获取文档详情 */
export function getDocument(id: number): Promise<Envelope<CampusDocument>> {
  return request.get(`/knowledge/${id}`)
}

/** 上传文档（FormData） */
export function uploadDocument(
  form: FormData,
  options?: { signal?: AbortSignal; onProgress?: (percent: number) => void },
): Promise<Envelope<UploadDocumentResponse>> {
  return request.post('/knowledge', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    signal: options?.signal,
    onUploadProgress: event => {
      if (!event.total) return
      options?.onProgress?.(Math.round((event.loaded / event.total) * 100))
    },
  })
}

/** 更新文档元数据 */
export function updateDocument(id: number, data: { title: string; category: string; source_url?: string; published_at?: string }): Promise<Envelope<CampusDocument>> {
  return request.patch(`/knowledge/${id}`, data)
}

/** 删除文档 */
export function deleteDocument(id: number): Promise<Envelope<null>> {
  return request.delete(`/knowledge/${id}`)
}

/** 预览文档内容 */
export function previewDocument(id: number, offset = 0, limit = 20000): Promise<Envelope<{ content: string; offset: number; limit: number; total_chars: number; has_more: boolean; format: string }>> {
  return request.get(`/knowledge/${id}/preview`, { params: { offset, limit } })
}

/** 重新索引文档 */
export function reindexDocument(id: number): Promise<Envelope<ReindexDocumentResponse>> {
  return request.post(`/knowledge/${id}/reindex`)
}
