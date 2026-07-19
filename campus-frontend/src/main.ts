import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
// 霞鹜文楷（屏幕阅读版）：display 字体，按 unicode-range 子集懒加载
import 'lxgw-wenkai-screen-webfont/lxgwwenkaiscreen.css'

import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)

// Pinia + 持久化
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)

// Router
app.use(router)

// Element Plus
app.use(ElementPlus, { size: 'default', locale: zhCn })

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
