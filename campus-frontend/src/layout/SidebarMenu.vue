<template>
  <template v-for="menu in menus" :key="menu.menuId">
    <el-sub-menu v-if="menu.menuType === 'M' && menu.children?.length" :index="menu.path || String(menu.menuId)">
      <template #title>
        <el-icon><component :is="getIcon(menu.icon)" /></el-icon>
        <span>{{ menu.menuName }}</span>
      </template>
      <SidebarMenu :menus="menu.children" />
    </el-sub-menu>
    <el-menu-item v-else-if="menu.menuType === 'C'" :index="normalisePath(menu.path)">
      <el-icon><component :is="getIcon(menu.icon)" /></el-icon>
      <template #title>{{ menu.menuName }}</template>
    </el-menu-item>
  </template>
</template>

<script setup lang="ts">
import * as Icons from '@element-plus/icons-vue'
import type { SysMenu } from '@/types'

defineProps<{ menus: ReadonlyArray<SysMenu> }>()

function normalisePath(path: string) {
  if (!path) return '/home'
  return path.startsWith('/') ? path : `/${path}`
}

function getIcon(name: string) {
  const icons = Icons as Record<string, unknown>
  const pascal = (name || 'Menu')
    .replace(/-\w/g, value => value.charAt(1).toUpperCase())
    .replace(/^\w/, value => value.toUpperCase())
  return icons[pascal] || Icons.Menu
}
</script>
