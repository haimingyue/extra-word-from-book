// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  devServer: {
    host: '0.0.0.0',
    port: 3000
  },
  experimental: {
    appManifest: false
  },
  css: ['element-plus/dist/index.css', '~/assets/css/theme.css'],
  app: {
    head: {
      title: '单词提取学习',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' }
      ]
    }
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api/v1'
    }
  },
  vite: {
    optimizeDeps: {
      include: ['element-plus']
    }
  }
})