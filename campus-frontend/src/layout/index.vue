<template>
  <el-container class="layout">
    <!-- 侧边栏：浅灰白背景，无边框 -->
    <el-aside :width="appStore.sidebarCollapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <img src="/favicon.svg" alt="" class="logo-img" />
        <span v-show="!appStore.sidebarCollapsed" class="logo-text">河海智问QA</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="appStore.sidebarCollapsed"
        :collapse-transition="false"
        router
        class="side-menu"
      >
        <SidebarMenu :menus="userStore.menus" />
      </el-menu>

      <!-- 底部快捷键提示 -->
      <div v-show="!appStore.sidebarCollapsed" class="sidebar-footer">
        <span class="hint-text">快速提问</span>
        <span><span class="kbd">Ctrl</span> <span class="kbd">K</span></span>
      </div>
    </el-aside>

    <!-- 右侧主体 -->
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="icon-btn" @click="appStore.toggleSidebar()">
            <Fold v-if="!appStore.sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-icon class="icon-btn" @click="appStore.toggleDark()" :title="appStore.isDark ? '切换亮色' : '切换暗色'">
            <Sunny v-if="appStore.isDark" />
            <Moon v-else />
          </el-icon>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" class="user-avatar">{{ userStore.user?.nickName?.charAt(0) || 'U' }}</el-avatar>
              <span class="username">{{ userStore.user?.nickName || userStore.user?.userName }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { ElMessageBox } from 'element-plus'
import SidebarMenu from './SidebarMenu.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

const activeMenu = computed(() => route.path)

// Ctrl/⌘ + K 快速跳转问答页
function handleShortcut(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    router.push('/home')
  }
}

// 页面刷新后恢复用户信息（token 已从 localStorage 恢复，但 user/permissions/roles 丢失）
onMounted(() => {
  if (userStore.token && !userStore.user) {
    userStore.fetchUserInfo().catch(() => {})
  }
  window.addEventListener('keydown', handleShortcut)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleShortcut)
})

function handleCommand(command: string) {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
      .then(() => {
        userStore.logout()
        router.push('/login')
      })
      .catch(() => {})
  }
}
</script>

<style scoped lang="scss">
.layout {
  height: 100vh;
}

// ---------- 侧边栏：浅苔绿（暗色模式自动切深） ----------
.sidebar {
  display: flex;
  flex-direction: column;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--sidebar-line);
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.3s cubic-bezier(0.22, 1, 0.36, 1);

  // 顶部环境光：一抹青绿辉光
  &::before {
    content: '';
    position: absolute;
    top: -80px;
    left: 50%;
    transform: translateX(-50%);
    width: 240px;
    height: 200px;
    background: radial-gradient(ellipse at center,
      rgba(52, 191, 163, 0.14), rgba(111, 220, 180, 0.05) 60%, transparent 75%);
    pointer-events: none;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px 20px;
    height: 56px;
    position: relative;
    .logo-img {
      width: 26px;
      height: 26px;
      filter: drop-shadow(0 0 8px rgba(52, 191, 163, 0.45));
    }
    .logo-text {
      font-family: var(--font-display);
      font-size: 17px;
      font-weight: 700;
      white-space: nowrap;
      letter-spacing: 0.05em;
      background: linear-gradient(90deg, var(--primary), var(--accent));
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
  }

  .side-menu {
    flex: 1;
    border-right: none;
    background: transparent;
    padding: 8px 10px;

    // 展开的子菜单容器默认是白底，改为透明融入侧边栏
    :deep(.el-menu--inline) {
      background: transparent;
    }

    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      height: 42px;
      line-height: 42px;
      margin: 2px 0;
      border-radius: 10px;
      color: var(--sidebar-text);
      background: transparent;
      transition: color 0.2s ease, background-color 0.2s ease, transform 0.2s ease;

      .el-icon { transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1); }

      &:hover {
        color: var(--sidebar-text-hover);
        background: var(--sidebar-hover);
        .el-icon { transform: translateX(1px) scale(1.1); }
      }
    }

    // 选中：青绿渐变胶囊 + 光晕
    :deep(.el-menu-item.is-active) {
      color: #fff;
      font-weight: 500;
      background: linear-gradient(135deg, rgba(14, 140, 114, 0.95), rgba(82, 199, 155, 0.8));
      box-shadow: 0 4px 14px rgba(14, 140, 114, 0.35);
    }

    :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
      color: var(--sidebar-text-hover);
    }

    :deep(.el-sub-menu .el-menu-item) {
      padding-left: 48px !important;
      height: 38px;
      line-height: 38px;
    }
  }

  .sidebar-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 20px;
    border-top: 1px solid var(--sidebar-line);
    .hint-text {
      font-size: 12px;
      color: var(--sidebar-text);
      opacity: 0.75;
      white-space: nowrap;
    }
    .kbd {
      color: var(--sidebar-text);
      background: var(--bg-card);
      border-color: var(--sidebar-line);
    }
  }
}

// ---------- 顶栏：玻璃拟态 ----------
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: color-mix(in srgb, var(--bg-card) 72%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  height: 56px;
  position: relative;
  z-index: 10;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .icon-btn {
    font-size: 18px;
    cursor: pointer;
    color: var(--text-secondary);
    padding: 6px;
    border-radius: 8px;
    transition: all 0.2s ease;
    &:hover {
      color: var(--accent);
      background: var(--accent-subtle);
      transform: rotate(-8deg) scale(1.08);
    }
  }

  .user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 4px 10px 4px 4px;
    border-radius: 999px;
    transition: background-color 0.2s ease;
    &:hover { background: var(--accent-subtle); }
    .user-avatar {
      background: var(--grad);
      font-size: 14px;
      box-shadow: 0 2px 8px rgba(14, 140, 114, 0.35);
    }
    .username {
      font-size: 14px;
      color: var(--primary-light);
    }
  }
}

.main-content {
  background:
    radial-gradient(1200px 500px at 85% -10%, rgba(15, 145, 121, 0.05), transparent 60%),
    radial-gradient(900px 400px at -10% 110%, rgba(82, 199, 155, 0.05), transparent 60%),
    var(--bg);
  padding: 24px 40px;
  overflow-y: auto;
}
</style>
