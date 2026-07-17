import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, removeToken } from '@/utils/auth'

const request = axios.create({
  baseURL: '',
  timeout: 30000
})

// 请求拦截器 — 注入 Token
request.interceptors.request.use(config => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, error => Promise.reject(error))

// 响应拦截器 — 统一错误处理
request.interceptors.response.use(
  response => {
    const { data } = response
    if (response.config.responseType === 'blob') return response
    if (data.code !== 200) {
      ElMessage.error(data.msg || data.message || '请求失败')
      return Promise.reject(new Error(data.msg || data.message))
    }
    return data
  },
  error => {
    if (error.response) {
      const { status } = error.response
      const url: string = error.config?.url || ''
      if (status === 401) {
        // QA / 知识库走 Python 后端，401 不强制跳登录
        if (url.startsWith('/qa/') || url.startsWith('/qa') || url.startsWith('/knowledge/') || url.startsWith('/knowledge')) {
          return Promise.reject(error)
        }
        ElMessage.error('登录已过期，请重新登录')
        removeToken()
        window.location.href = '/login'
      } else if (status === 403) {
        ElMessage.error('权限不足')
      } else {
        // Python 后端错误信息在 detail（FastAPI HTTPException）或 message，Java 侧在 msg
        const data = error.response.data
        const serverMsg = data?.detail || data?.message || data?.msg
        ElMessage.error(serverMsg || `服务器错误: ${status}`)
      }
    } else {
      ElMessage.error('网络异常，请检查连接')
    }
    return Promise.reject(error)
  }
)

export default request
