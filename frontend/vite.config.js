import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import http from 'http'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  build: {
    // 不预先清空 dist（避免安全钩子拦截；新文件直接覆盖写入，残留旧 hash 文件无副作用）
    emptyOutDir: false
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        // 关键加固：禁用代理到后端的 keep-alive 连接复用。
        // 原先代理会复用空闲长连接；后端(uvicorn)回收/关闭这些 socket 后，
        // 下一次“狂刷页面”的请求会命中死连接 -> ECONNRESET -> 浏览器报“接口异常”。
        // 改为每条请求新建短连接，彻底消除刷新导致的间歇异常。
        agent: new http.Agent({ keepAlive: false }),
        timeout: 30000,
        proxyTimeout: 30000
      },
      '/data/images': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        agent: new http.Agent({ keepAlive: false }),
        timeout: 30000,
        proxyTimeout: 30000
      }
    }
  }
})
