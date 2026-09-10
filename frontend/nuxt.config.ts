// https://nuxt.com/docs/api/configuration/nuxt-config
import { defineNuxtConfig } from 'nuxt/config'

declare const process: {
  env: Record<string, string | undefined>
}

export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  devtools: { enabled: true },

  app: {
    head: {
      title: 'WashQueue — Smart Hostel Laundry Hub',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Real-time hostel laundry telemetry and booking queue' }
      ],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400;1,600&family=JetBrains+Mono:wght@500;600;700&display=swap'
        }
      ]
    }
  },

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
