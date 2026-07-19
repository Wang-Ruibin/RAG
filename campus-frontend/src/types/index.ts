// 统一响应格式
export interface R<T> {
  code: number
  msg: string
  data: T
}

// 分页结果
export interface PageResult<T> {
  rows: T[]
  total: number
  pageNum: number
  pageSize: number
}

// 用户
export interface SysUser {
  userId: number
  userName: string
  nickName: string
  email: string
  phone: string
  sex: string
  avatar: string
  status: string
  createTime: string
  remark: string
}

// 角色
export interface SysRole {
  roleId: number
  roleName: string
  roleKey: string
  roleSort: number
  status: string
  remark: string
}

// 菜单
export interface SysMenu {
  menuId: number
  menuName: string
  parentId: number
  orderNum: number
  path: string
  component: string
  menuType: string
  perms: string
  icon: string
  children?: SysMenu[]
}

// 知识分类（Java 退役后删除）
export interface KnowledgeCategory {
  categoryId: number
  parentId: number
  categoryName: string
  categoryKey: string
  sortOrder: number
  icon: string
  docCount?: number
}

// 知识文档（旧 Java 模型，保留兼容）
export interface KnowledgeDocument {
  docId: number
  title: string
  categoryId: number
  content: string
  sourceUrl: string
  keywords: string
  status: string
  viewCount: number
  createTime: string
  updateTime: string
}

// ========== Python RAG 模型（新） ==========

// 对话会话
export interface Conversation {
  id: number
  title: string
  message_count: number
  created_at: string
  updated_at: string
  messages?: ChatMessage[]
}

// 管理员问答管理列表项
export interface QaConversationItem {
  conversation_id: number
  conversation_title: string
  question: string
  answer: string
  sources: SourceRef[]
  user_id: number
  user_name: string
  answer_origin: 'KNOWLEDGE_BASE' | 'WEB_SEARCH' | 'HYBRID' | 'NO_ANSWER' | null
  status: 'STREAMING' | 'COMPLETE' | 'CANCELLED' | 'ERROR' | null
  created_at: string
}

// 聊天消息
export interface ChatMessage {
  id?: number
  client_id?: string
  request_id?: string
  role: 'USER' | 'ASSISTANT'
  content: string
  sources: SourceRef[]
  status?: 'STREAMING' | 'COMPLETE' | 'CANCELLED' | 'ERROR'
  latency_ms?: number | null
  answer_origin?: 'KNOWLEDGE_BASE' | 'WEB_SEARCH' | 'HYBRID' | 'NO_ANSWER' | null
  created_at?: string
  model?: string | null
  knowledge_task?: AnswerKnowledgeTask | null
  correction?: AnswerCorrection | null
}

// 答案沉淀任务（点赞入库）
export interface AnswerKnowledgeTask {
  id: number
  assistant_message_id: number | null
  status: 'QUEUED' | 'PROCESSING' | 'COMPLETE' | 'FAILED'
  document_id: number | null
  qa_entry_id: number | null
  cleaned_title: string | null
  error: string | null
  created_at: string
  updated_at: string
  finished_at: string | null
}

// 答案纠错
export interface AnswerCorrection {
  id: number
  assistant_message_id: number | null
  status: 'PENDING' | 'PROCESSING' | 'APPROVED' | 'REJECTED' | 'FAILED'
  proposed_answer: string
  reviewed_question: string | null
  reviewed_answer: string | null
  review_note: string | null
  approved_document_id: number | null
  error: string | null
  created_at: string
  updated_at: string
  reviewed_at: string | null
}

// 纠错审核（管理端扩展字段）
export interface AdminAnswerCorrection extends AnswerCorrection {
  user_id: number
  contributor_name: string | null
  contributor_email: string | null
  original_question: string | null
  original_answer: string | null
  original_sources: SourceRef[]
  source_document_ids: number[]
}

// 引用来源
export interface SourceRef {
  chunk_id?: number | string
  document_id?: number | string
  title?: string
  score?: number
  snippet?: string
  content?: string
  source_type?: string
  citation_index?: number
  url?: string
  source_url?: string
  site_name?: string
  domain?: string
  published_at?: string
}

// 知识库文档（Python 模型）
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
  uploaded_by?: number
  created_at: string
  updated_at: string
}

// 文档预览（Python 后端）
export interface DocumentPreview {
  content: string
  offset: number
  limit: number
  total_chars: number
  has_more: boolean
  format: string
}

// Python 统一响应信封
export interface Envelope<T> {
  code: number
  message: string
  data: T
  timestamp?: string
}

export interface ActiveChatStream {
  requestId: string
  requestedConversationId: number | string | null
  serverConversationId: number | string | null
  controller: AbortController
  assistantMessageId: string
}

// 系统日志
export interface SysOperLog {
  operId: number
  title: string
  businessType: number
  operName: string
  method?: string
  requestMethod?: string
  operUrl: string
  operIp: string
  operParam?: string
  jsonResult?: string
  status: number
  errorMsg?: string
  operTime: string
  costTime: number
}

// 登录
export interface LoginForm {
  username: string
  password: string
  uuid: string
  code: string
}

export interface RegisterForm {
  username: string
  password: string
  nickName: string
  email?: string
  phone?: string
  uuid: string
  code: string
}

export interface CaptchaResult {
  uuid: string
  img: string
}

export interface LoginResult {
  token: string
  tokenName: string
}

export interface UserInfo {
  user: SysUser
  permissions: string[]
  roles: string[]
}
