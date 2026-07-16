/** Token 存储 —— 独立于 Pinia 的唯一真相源，对齐水投 @/utils/auth 架构 */

const TOKEN_KEY = 'campus-token'
const OLD_KEY = 'campus-user' // 旧版 persist 插件格式兼容

/** 获取 token（纯字符串，无 Bearer 前缀） */
export function getToken(): string {
  let token = localStorage.getItem(TOKEN_KEY)
  if (token) return token
  // 迁移：旧版 pinia-plugin-persistedstate 格式 {"token":"eyJ..."}
  try {
    const raw = localStorage.getItem(OLD_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      token = parsed.token || ''
      if (token) {
        setToken(token)
        localStorage.removeItem(OLD_KEY)
      }
    }
  } catch { /* ignore */ }
  return token || ''
}

/** 持久化 token */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

/** 删除 token */
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(OLD_KEY)
}
