import request from './request'
import type { R, PageResult, SysRole } from '@/types'

export interface CreateRoleInput {
  roleName: string
  roleKey: string
  roleSort: number
  status: string
  remark: string
}

export interface UpdateRoleInput extends CreateRoleInput {
  roleId: number
}

export function listRole(params: any): Promise<R<PageResult<SysRole>>> {
  return request.get('/system/role/list', { params })
}

export function addRole(data: CreateRoleInput, menuIds?: number[]): Promise<R<void>> {
  return request.post('/system/role', data, { params: { menuIds: menuIds?.join(',') } })
}

export function updateRole(data: UpdateRoleInput, menuIds?: number[]): Promise<R<void>> {
  return request.put('/system/role', data, { params: { menuIds: menuIds?.join(',') } })
}

export function deleteRoles(roleIds: number[]): Promise<R<void>> {
  return request.delete(`/system/role/${roleIds.join(',')}`)
}

export function getRoleMenus(roleId: number): Promise<R<number[]>> {
  return request.get(`/system/role/${roleId}/menus`)
}
