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
  chunk_id: number
  document_id: number
  title: string
  source_url?: string | null
  published_at?: string | null
  score: number
  snippet: string
  citation_index?: number
}

export interface ChatMessage {
  id?: number
  role: 'USER' | 'ASSISTANT'
  content: string
  sources: SourceRef[]
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
