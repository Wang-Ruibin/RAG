import request from './request'
import type { R, PageResult, SysUser } from '@/types'

export function listUser(params: any): Promise<R<PageResult<SysUser>>> {
  return request.get('/system/user/list', { params })
}

export function addUser(data: SysUser, roleIds?: number[]): Promise<R<void>> {
  const params: any = {}
  if (roleIds?.length) params.roleIds = roleIds.join(',')
  return request.post('/system/user', data, { params })
}

export function updateUser(data: SysUser, roleIds?: number[]): Promise<R<void>> {
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
