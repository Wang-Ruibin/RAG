import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { login as loginApi, guestLogin as guestLoginApi, getUserInfo } from '@/api/auth'
import { getRouters } from '@/api/menu'
import { getToken, setToken, removeToken, getGuestFlag, setGuestFlag } from '@/utils/auth'
import type { SysUser, SysMenu } from '@/types'

export const useUserStore = defineStore('user', () => {
  const token = ref(getToken())
  const user = ref<SysUser | null>(null)
  const permissions = ref<string[]>([])
  const roles = ref<string[]>([])
  const menus = ref<SysMenu[]>([])
  // localStorage 标志兜底：硬刷新时守卫同步执行，roles 还没拉回来
  const guestFlag = ref(getGuestFlag())
  const isGuest = computed(() => guestFlag.value || roles.value.includes('guest'))

  async function login(username: string, password: string, uuid: string, code: string) {
    setGuestFlag(false)
    guestFlag.value = false
    const res = await loginApi({ username, password, uuid, code })
    token.value = res.data.token
    setToken(res.data.token)
    await fetchUserInfo()
  }

  /** 访客登录：拿真 token，getInfo/routers 正常工作（菜单只剩首页），问答不落库 */
  async function guestLogin() {
    const res = await guestLoginApi()
    token.value = res.data.token
    setToken(res.data.token)
    setGuestFlag(true)
    guestFlag.value = true
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
    // 纯本地清理，不调 /auth/logout（访客独立 token，无需服务端注销）
    setGuestFlag(false)
    guestFlag.value = false
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

  return { token, user, permissions, roles, menus, isGuest, login, guestLogin, fetchUserInfo, logout, hasPermission }
})
