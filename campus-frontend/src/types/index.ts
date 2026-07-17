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

// 聊天消息
export interface ChatMessage {
  id?: number
  role: 'USER' | 'ASSISTANT'
  content: string
  sources: SourceRef[]
  status?: 'STREAMING' | 'COMPLETE' | 'CANCELLED' | 'ERROR'
  latency_ms?: number | null
}

// 引用来源
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

// Python 统一响应信封
export interface Envelope<T> {
  code: number
  message: string
  data: T
  timestamp?: string
}

// 系统日志
export interface SysOperLog {
  operId: number
  title: string
  businessType: number
  operName: string
  operUrl: string
  operIp: string
  status: number
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
