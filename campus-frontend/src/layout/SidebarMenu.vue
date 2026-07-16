<template>
  <template v-for="menu in menus" :key="menu.menuId">
    <!-- 目录：有子节点，渲染为子菜单 -->
    <el-sub-menu v-if="menu.menuType === 'M' && menu.children?.length" :index="menu.path || String(menu.menuId)">
      <template #title>
        <el-icon v-if="menu.icon"><component :is="getIcon(menu.icon)" /></el-icon>
        <span>{{ menu.menuName }}</span>
      </template>
      <SidebarMenu :menus="menu.children" />
    </el-sub-menu>

    <!-- 菜单项 -->
    <el-menu-item v-else-if="menu.menuType === 'C'" :index="menu.path">
      <el-icon v-if="menu.icon"><component :is="getIcon(menu.icon)" /></el-icon>
      <span>{{ menu.menuName }}</span>
    </el-menu-item>
  </template>
</template>

<script setup lang="ts">
import * as Icons from '@element-plus/icons-vue'

defineProps<{ menus: any[] }>()

function getIcon(name: string): any {
  if (!name) return null
  const icons = Icons as Record<string, any>
  if (icons[name]) return icons[name]
  const pascal = name
    .replace(/-\w/g, s => s.charAt(1).toUpperCase())
    .replace(/^\w/, s => s.toUpperCase())
  return icons[pascal] || icons['Menu']
}
</script>
