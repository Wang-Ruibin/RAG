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

// 知识分类
export interface KnowledgeCategory {
  categoryId: number
  parentId: number
  categoryName: string
  categoryKey: string
  sortOrder: number
  icon: string
  docCount?: number
}

// 知识文档
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
