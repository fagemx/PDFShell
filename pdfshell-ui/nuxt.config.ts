// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-05-15',
  devtools: { enabled: true },
  modules: [
    '@nuxt/eslint',
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
  ],
  css: ['~/assets/css/tailwind.css'],
  
  routeRules: {
    // 允許 API 下載路徑被嵌入 iframe
    '/api/v1/public-files/download/**': {
      headers: {
        'X-Frame-Options': 'SAMEORIGIN',
      }
    },
    '/api/v1/download/**': { // 針對會話檔案下載的路徑
      headers: {
        'X-Frame-Options': 'SAMEORIGIN',
      }
    }
  },

  vite: {
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000', // 您的 Django 伺服器地址
          changeOrigin: true,
        }
      }
    }
  }
})