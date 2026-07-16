import request from './request'
import type { R, PageResult, KnowledgeCategory, KnowledgeDocument } from '@/types'

// 分类
export function listCategory(): Promise<R<KnowledgeCategory[]>> {
  return request.get('/knowledge/category/list')
}

export function categoryTree(): Promise<R<KnowledgeCategory[]>> {
  return request.get('/knowledge/category/tree')
}

export function addCategory(data: KnowledgeCategory): Promise<R<void>> {
  return request.post('/knowledge/category', data)
}

export function updateCategory(data: KnowledgeCategory): Promise<R<void>> {
  return request.put('/knowledge/category', data)
}

export function deleteCategories(ids: number[]): Promise<R<void>> {
  return request.delete(`/knowledge/category/${ids.join(',')}`)
}

// 文档
export function listDocument(params: any): Promise<R<PageResult<KnowledgeDocument>>> {
  return request.get('/knowledge/document/list', { params })
}

export function getDocument(docId: number): Promise<R<KnowledgeDocument>> {
  return request.get(`/knowledge/document/${docId}`)
}

export function addDocument(data: KnowledgeDocument): Promise<R<void>> {
  return request.post('/knowledge/document', data)
}

export function updateDocument(data: KnowledgeDocument): Promise<R<void>> {
  return request.put('/knowledge/document', data)
}

export function deleteDocuments(ids: number[]): Promise<R<void>> {
  return request.delete(`/knowledge/document/${ids.join(',')}`)
}
