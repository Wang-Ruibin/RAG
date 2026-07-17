import type { Envelope } from '../types'

const TOKEN_KEY = 'campusqa_token'

export const authToken = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (value: string) => localStorage.setItem(TOKEN_KEY, value),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = authToken.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...init, headers })
  const payload = (await response.json()) as Envelope<T>
  if (!response.ok) throw new Error(payload.message || `请求失败 (${response.status})`)
  return payload.data
}

export async function apiBlob(path: string): Promise<Blob> {
  const headers = new Headers()
  const token = authToken.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { headers })
  if (!response.ok) {
    let errorMessage = `请求失败 (${response.status})`
    try {
      const payload = (await response.json()) as Envelope<unknown>
      errorMessage = payload.message || errorMessage
    } catch {
      // Binary endpoints may not return a JSON error body.
    }
    throw new Error(errorMessage)
  }
  return response.blob()
}
