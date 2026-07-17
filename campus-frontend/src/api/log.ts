import request from './request'
import type { R, PageResult, SysOperLog } from '@/types'

export function listLog(params: any): Promise<R<PageResult<SysOperLog>>> {
  return request.get('/system/log/list', { params })
}

export function deleteLogs(operIds: number[]): Promise<R<void>> {
  return request.delete(`/system/log/${operIds.join(',')}`)
}

export function cleanLog(): Promise<R<void>> {
  return request.delete('/system/log/clean')
}

/** 导出日志 Excel（携带当前搜索条件，返回 blob） */
export function exportLog(params: any): Promise<any> {
  return request.get('/system/log/export', { params, responseType: 'blob' })
}
