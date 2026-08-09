// https://nuxt.com/docs/api/configuration/nuxt-config
import { defineNuxtConfig } from 'nuxt/config'

declare const process: {
  env: Record<string, string | undefined>
}

export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  devtools: { enabled: true },

  // Register Tailwind CSS module
  modules: [
    '@nuxtjs/tailwindcss'
  ],

  // Enable polling for Vite HMR inside Docker containers
  vite: {
    server: {
      watch: {
        usePolling: true
      }
    }
  },

  // Expose configuration keys to client/server
  runtimeConfig: {
    public: {
      supabaseUrl: process.env.SUPABASE_URL || '',
      supabaseKey: process.env.SUPABASE_KEY || '',
      apiBaseUrl: process.env.API_BASE_URL || 'http://localhost:8000'
    }
  }
})
