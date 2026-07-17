import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login/index.vue'),
      meta: { title: '登录' }
    },
    {
      path: '/',
      component: () => import('@/layout/index.vue'),
      redirect: '/home',
      children: [
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/home/index.vue'),
          meta: { title: '首页', icon: 'HomeFilled' }
        },
        {
          path: 'knowledge/category',
          redirect: '/knowledge/document'  // 分类功能已迁移至 Python，重定向到文档管理
        },
        {
          path: 'knowledge/document',
          name: 'KnowledgeDocument',
          component: () => import('@/views/knowledge/document/index.vue'),
          meta: { title: '知识库管理', icon: 'Document' }
        },
        {
          path: 'knowledge/correction',
          name: 'KnowledgeCorrection',
          component: () => import('@/views/knowledge/correction/index.vue'),
          meta: { title: '纠错审核', icon: 'EditPen' }
        },
        {
          path: 'system/user',
          name: 'SystemUser',
          component: () => import('@/views/system/user/index.vue'),
          meta: { title: '用户管理', icon: 'User' }
        },
        {
          path: 'system/role',
          name: 'SystemRole',
          component: () => import('@/views/system/role/index.vue'),
          meta: { title: '角色管理', icon: 'Avatar' }
        },
        {
          path: 'system/log',
          name: 'SystemLog',
          component: () => import('@/views/system/log/index.vue'),
          meta: { title: '系统日志', icon: 'Tickets' }
        }
      ]
    }
  ]
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || 'CampusQA'} - 校园知识问答`

  const userStore = useUserStore()
  if (to.path !== '/login' && !userStore.token) {
    next('/login')
  } else if (to.path === '/login' && userStore.token) {
    next('/home')
  } else {
    next()
  }
})

export default router
