import request from './request'
import type { R, PageResult, SysUser } from '@/types'

export interface AssignUserRolesInput {
  userId: number
  roleIds: number[]
}

export interface UserListParams {
  pageNum: number
  pageSize: number
  userName?: string
  nickName?: string
  phone?: string
  status?: string
}

export interface CreateUserInput {
  userName: string
  nickName: string
  email: string
  phone: string
  status: string
  password: string
  remark?: string
}

export interface UpdateUserInput extends Omit<CreateUserInput, 'password'> {
  userId: number
}

export function listUser(params: UserListParams): Promise<R<PageResult<SysUser>>> {
  return request.get('/system/user/list', { params })
}

export function addUser(data: CreateUserInput, roleIds?: number[]): Promise<R<void>> {
  const params: any = {}
  if (roleIds?.length) params.roleIds = roleIds.join(',')
  return request.post('/system/user', data, { params })
}

export function updateUser(data: UpdateUserInput, roleIds?: number[]): Promise<R<void>> {
  const params: any = {}
  if (roleIds?.length) params.roleIds = roleIds.join(',')
  return request.put('/system/user', data, { params })
}

export function deleteUsers(userIds: number[]): Promise<R<void>> {
  return request.delete(`/system/user/${userIds.join(',')}`)
}

export function resetPassword(userId: number, password: string): Promise<R<void>> {
  return request.put('/system/user/resetPwd', { userId, password })
}

export function getUserRoles(userId: number): Promise<R<number[]>> {
  return request.get(`/system/user/${userId}/roles`)
}

export function assignUserRoles(input: AssignUserRolesInput): Promise<R<void>> {
  return request.put('/system/user', { userId: input.userId }, {
    params: { roleIds: input.roleIds.join(',') },
  })
}
