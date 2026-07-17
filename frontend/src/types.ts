export type Role = 'STUDENT' | 'ADMIN'

export interface User {
  id: number
  name: string
  email: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface SourceRef {
  source_type?: 'KNOWLEDGE_BASE' | 'WEB_SEARCH' | string | null
  chunk_id?: number | null
  document_id?: number | null
  title: string
  url?: string | null
  source_url?: string | null
  published_at?: string | null
  score?: number | null
  snippet: string
  content?: string | null
  site_name?: string | null
  domain?: string | null
  citation_index?: number
}

export type AnswerOrigin = 'KNOWLEDGE_BASE' | 'WEB_SEARCH' | 'NO_ANSWER'

export interface AnswerKnowledgeTask {
  id: number
  assistant_message_id: number
  status: 'QUEUED' | 'PROCESSING' | 'COMPLETE' | 'FAILED'
  document_id?: number | null
  cleaned_title?: string | null
  error?: string | null
  created_at: string
  updated_at: string
  finished_at?: string | null
}

export interface ChatMessage {
  id?: number
  role: 'USER' | 'ASSISTANT'
  content: string
  sources: SourceRef[]
  answer_origin?: AnswerOrigin | null
  knowledge_task?: AnswerKnowledgeTask | null
  status?: 'STREAMING' | 'COMPLETE' | 'CANCELLED' | 'ERROR'
  latency_ms?: number | null
}

export interface Conversation {
  id: number
  title: string
  message_count: number
  created_at: string
  updated_at: string
  messages?: ChatMessage[]
}

export interface CampusDocument {
  id: number
  title: string
  original_name: string
  mime_type: string
  size: number
  category: string
  source_url?: string | null
  published_at?: string | null
  status: 'QUEUED' | 'PROCESSING' | 'READY' | 'FAILED' | 'DELETING'
  stage: string
  error?: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface Envelope<T> {
  code: number
  message: string
  data: T
  timestamp: string
}
