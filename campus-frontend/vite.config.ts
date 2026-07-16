import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

// 浏览器页面导航请求不代理，留给 SPA fallback 处理
const bypassPage = (req: any) => {
  if (req.headers?.accept?.includes('text/html')) {
    return '/index.html'
  }
}

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia']
    }),
    Components({
      resolvers: [ElementPlusResolver()]
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 9090,
    proxy: {
      '/auth': {
        target: 'http://localhost:19280',
        changeOrigin: true,
        bypass: bypassPage
      },
      '/system': {
        target: 'http://localhost:19280',
        changeOrigin: true,
        bypass: bypassPage
      },
      '/knowledge': {
        target: 'http://localhost:19280',
        changeOrigin: true,
        bypass: bypassPage
      },
      '/qa': {
        target: 'http://localhost:19280',
        changeOrigin: true,
        bypass: bypassPage
      }
    }
  }
})
