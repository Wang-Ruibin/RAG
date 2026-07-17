import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getUserInfo } from '@/api/auth'
import { getRouters } from '@/api/menu'
import { getToken, setToken, removeToken } from '@/utils/auth'
import type { SysUser, SysMenu } from '@/types'

export const useUserStore = defineStore('user', () => {
  const token = ref(getToken())
  const user = ref<SysUser | null>(null)
  const permissions = ref<string[]>([])
  const roles = ref<string[]>([])
  const menus = ref<SysMenu[]>([])

  async function login(username: string, password: string, uuid: string, code: string) {
    const res = await loginApi({ username, password, uuid, code })
    token.value = res.data.token
    setToken(res.data.token)
    await fetchUserInfo()
  }

  async function fetchUserInfo() {
    const res = await getUserInfo()
    user.value = res.data.user
    permissions.value = res.data.permissions
    roles.value = res.data.roles
    // 加载菜单路由
    try {
      const menuRes = await getRouters()
      menus.value = menuRes.data || []
    } catch { menus.value = [] }
  }

  function logout() {
    token.value = ''
    removeToken()
    user.value = null
    permissions.value = []
    roles.value = []
    menus.value = []
  }

  function hasPermission(perm: string): boolean {
    return permissions.value.includes(perm) || roles.value.includes('admin')
  }

  return { token, user, permissions, roles, menus, login, fetchUserInfo, logout, hasPermission }
})
