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
