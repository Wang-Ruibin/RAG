<template>
  <el-container class="app-layout">
    <el-aside :width="appStore.sidebarCollapsed ? '76px' : '260px'" class="app-sidebar">
      <div class="brand-block">
        <AppLogo :compact="appStore.sidebarCollapsed" />
        <div v-if="!appStore.sidebarCollapsed" class="brand-platform"><strong>河海智问</strong><span>校园知识智能问答平台</span></div>
      </div>

      <el-menu :default-active="route.path" :collapse="appStore.sidebarCollapsed" :collapse-transition="false" router class="nav-menu">
        <SidebarMenu :menus="displayMenus" />
      </el-menu>

      <CampusPhoto
        v-if="!appStore.sidebarCollapsed && route.path !== '/home'"
        class="sidebar-art"
        :src="sidebarCampus.src"
        :alt="sidebarCampus.alt"
        :caption="sidebarCampus.caption"
      />

      <el-dropdown placement="top-start" trigger="click" @command="handleCommand">
        <button :class="['sidebar-user', { collapsed: appStore.sidebarCollapsed }]" type="button">
          <el-avatar :size="38">{{ userInitial }}</el-avatar>
          <span v-if="!appStore.sidebarCollapsed" class="sidebar-user__copy">
            <strong>{{ userStore.user?.nickName || userStore.user?.userName || '用户' }}</strong>
            <small v-if="primaryRole">{{ primaryRole }}</small>
          </span>
          <el-icon v-if="!appStore.sidebarCollapsed"><ArrowUp /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-aside>

    <el-container class="app-workspace">
      <el-header v-if="route.path !== '/home'" class="app-header">
        <div class="header-main">
          <button class="icon-action" type="button" :aria-label="appStore.sidebarCollapsed ? '展开侧栏' : '收起侧栏'" @click="appStore.toggleSidebar()">
            <el-icon><Expand v-if="appStore.sidebarCollapsed" /><Fold v-else /></el-icon>
          </button>
          <div class="header-titles">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item>河海智问</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>
        <button class="icon-action" type="button" :aria-label="appStore.isDark ? '切换浅色模式' : '切换深色模式'" @click="appStore.toggleDark()">
          <el-icon><Sunny v-if="appStore.isDark" /><Moon v-else /></el-icon>
        </button>
      </el-header>
      <el-main :class="['app-main', { 'app-main--chat': route.path === '/home' }]">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in"><component :is="Component" /></transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ArrowUp, Expand, Fold, Moon, Sunny, SwitchButton } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import type { SysMenu } from '@/types'
import AppLogo from '@/components/AppLogo.vue'
import CampusPhoto from '@/components/CampusPhoto.vue'
import SidebarMenu from './SidebarMenu.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

const currentTitle = computed(() => String(route.meta.title || '河海智问'))
const primaryRole = computed(() => userStore.roles[0] || '')
const userInitial = computed(() => (userStore.user?.nickName || userStore.user?.userName || 'U').charAt(0))

const sidebarCampus = computed(() => {
  if (route.path.includes('/knowledge')) return { src: '/assets/xikang-campus-08.jpg', alt: '河海大学西康路校区建筑', caption: '西康路校区' }
  if (route.path.includes('/system/user')) return { src: '/assets/xikang-campus-01.jpg', alt: '河海大学西康路校区校园建筑', caption: '西康路校区' }
  if (route.path.includes('/system/role')) return { src: '/assets/xikang-campus-03.jpg', alt: '河海大学西康路校区工程馆', caption: '西康路校区 · 工程馆' }
  if (route.path.includes('/system/log')) return { src: '/assets/xikang-campus-02.jpg', alt: '河海大学西康路校区校园建筑', caption: '西康路校区' }
  return { src: '/assets/jiangning-library.jpg', alt: '河海大学江宁校区图书馆', caption: '江宁校区图书馆' }
})

const iconByPath: Record<string, string> = {
  '/home': 'ChatDotRound',
  '/knowledge/document': 'Collection',
  '/system/user': 'User',
  '/system/role': 'Key',
  '/system/log': 'Tickets',
}

function cloneMenu(menu: SysMenu): SysMenu | null {
  if (menu.menuType === 'F') return null
  const children = (menu.children || []).map(cloneMenu).filter((item): item is SysMenu => item !== null)
  const path = menu.path?.startsWith('/') ? menu.path : menu.path ? `/${menu.path}` : ''
  const copy: SysMenu = {
    ...menu,
    menuName: path === '/home' ? '智能问答' : menu.menuName,
    icon: iconByPath[path] || menu.icon || 'Menu',
    children,
  }
  if (copy.menuType === 'M' && children.length === 1 && children[0].path.includes('knowledge')) {
    return { ...children[0], menuName: copy.menuName || children[0].menuName, icon: 'Collection' }
  }
  return copy
}

const displayMenus = computed<ReadonlyArray<SysMenu>>(() =>
  userStore.menus.map(cloneMenu).filter((item): item is SysMenu => item !== null),
)

onMounted(() => {
  if (userStore.token && !userStore.user) userStore.fetchUserInfo().catch(() => undefined)
})

async function handleCommand(command: string) {
  if (command !== 'logout') return
  try {
    await ElMessageBox.confirm('确定退出当前账号吗？', '退出登录', { type: 'warning' })
    userStore.logout()
    await router.push('/login')
  } catch { /* user cancelled */ }
}
</script>

<style scoped>
.app-layout { height:100vh; background:var(--page); overflow:hidden; }
.app-sidebar { position:relative; display:flex; flex-direction:column; overflow:hidden; background:var(--sidebar); border-right:1px solid var(--border); transition:width .25s ease; }
.brand-block { display:flex; min-height:148px; flex-direction:column; align-items:flex-start; justify-content:center; gap:10px; padding:18px 22px 16px; border-bottom:1px solid var(--border); }
.brand-platform{display:flex;flex-direction:column;padding-left:70px}.brand-platform strong{color:var(--brand);font-size:20px;line-height:1.15;letter-spacing:.08em}.brand-platform span{margin-top:4px;color:var(--text-muted);font-size:10px;white-space:nowrap}
.nav-menu { flex:1; padding:16px 12px; overflow:auto; border:0; background:transparent; }
.nav-menu:not(.el-menu--collapse) { width:100%; }
.nav-menu :deep(.el-menu-item), .nav-menu :deep(.el-sub-menu__title) { height:46px; margin:4px 0; border-radius:11px; color:var(--text-secondary); }
.nav-menu :deep(.el-menu-item:hover), .nav-menu :deep(.el-sub-menu__title:hover) { color:var(--brand); background:var(--brand-soft); }
.nav-menu :deep(.el-menu-item.is-active) { color:var(--brand); background:linear-gradient(90deg,var(--brand-soft),color-mix(in srgb,var(--brand-soft) 40%,transparent)); font-weight:700; }
.nav-menu :deep(.el-menu-item.is-active)::before { position:absolute; left:0; width:3px; height:24px; content:''; background:var(--brand); border-radius:0 4px 4px 0; }
.nav-menu :deep(.el-menu--inline) { background:transparent; }
.sidebar-art { position:absolute; right:0; bottom:76px; width:100%; height:210px; }
.sidebar-art :deep(img) { object-position:center 35%; }
.sidebar-user { position:relative; z-index:2; display:flex; align-items:center; width:calc(100% - 24px); min-height:62px; margin:0 12px 14px; padding:10px 12px; color:var(--text-secondary); text-align:left; background:var(--surface); border:1px solid var(--border); border-radius:13px; box-shadow:var(--shadow-sm); cursor:pointer; }
.sidebar-user.collapsed { justify-content:center; padding:8px; }
.sidebar-user .el-avatar { flex:0 0 auto; color:#fff; background:linear-gradient(135deg,var(--brand),var(--brand-light)); }
.sidebar-user__copy { display:flex; min-width:0; flex:1; flex-direction:column; margin-left:10px; }
.sidebar-user__copy strong { overflow:hidden; color:var(--text); font-size:14px; text-overflow:ellipsis; white-space:nowrap; }
.sidebar-user__copy small { overflow:hidden; color:var(--text-muted); text-overflow:ellipsis; white-space:nowrap; }
.app-workspace { min-width:0; }
.app-header { display:flex; align-items:center; justify-content:space-between; height:78px; padding:0 36px; background:color-mix(in srgb,var(--surface) 94%,transparent); border-bottom:1px solid var(--border); }
.header-main { display:flex; align-items:center; gap:16px; }
.icon-action { display:grid; width:38px; height:38px; place-items:center; color:var(--text-secondary); background:var(--surface-soft); border:1px solid var(--border); border-radius:10px; cursor:pointer; }
.icon-action:hover { color:var(--brand); border-color:color-mix(in srgb,var(--brand) 40%,var(--border)); }
.header-titles { display:flex; flex-direction:column; gap:3px; }
.header-titles :deep(.el-breadcrumb__inner) { color:var(--text-secondary); font-size:14px; font-weight:400; }
.app-main { min-width:0; padding:26px 36px; overflow:auto; }
.app-main--chat{padding:16px 18px}
@media(max-width:900px){.app-main{padding:22px 18px}.app-header{padding:0 18px}}
@media(max-width:640px){.app-sidebar{position:absolute;z-index:50;height:100%;box-shadow:var(--shadow-md)}.app-sidebar[style*="248px"] + .app-workspace{margin-left:76px}.header-titles :deep(.el-breadcrumb){display:none}}
</style>
