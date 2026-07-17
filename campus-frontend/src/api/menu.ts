import request from './request'
import type { R, SysMenu } from '@/types'

/** 全部菜单树（角色管理用） */
export function listMenu(): Promise<R<SysMenu[]>> {
  return request.get('/system/menu/tree')
}

/** 当前用户路由菜单（侧边栏用，已按权限过滤） */
export function getRouters(): Promise<R<SysMenu[]>> {
  return request.get('/system/user/routers')
}
