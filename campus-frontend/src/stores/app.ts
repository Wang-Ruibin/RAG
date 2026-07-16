import { defineStore } from 'pinia'
import { ref } from 'vue'

const DARK_KEY = 'campus-dark'

function initDark(): boolean {
  const saved = localStorage.getItem(DARK_KEY)
  if (saved !== null) return saved === '1'
  // 无手动偏好时跟随系统
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const isDark = ref(initDark())

  // 初始化时同步到 html
  document.documentElement.classList.toggle('dark', isDark.value)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function toggleDark() {
    isDark.value = !isDark.value
    document.documentElement.classList.toggle('dark', isDark.value)
    localStorage.setItem(DARK_KEY, isDark.value ? '1' : '0')
  }

  return { sidebarCollapsed, toggleSidebar, isDark, toggleDark }
})
