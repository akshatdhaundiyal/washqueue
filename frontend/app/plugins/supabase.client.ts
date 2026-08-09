import { createClient } from '@supabase/supabase-js'

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()

  const supabaseUrl = config.public.supabaseUrl
  const supabaseKey = config.public.supabaseKey

  // If Supabase environment variables are missing, run 100% locally
  if (!supabaseUrl || !supabaseKey) {
    console.log('ℹ️ Supabase URL not configured. Running in 100% Local LAN WebSocket mode.')
    return {
      provide: {
        supabase: null
      }
    }
  }

  try {
    const supabase = createClient(supabaseUrl, supabaseKey)
    return {
      provide: {
        supabase
      }
    }
  } catch (err) {
    console.warn('Failed to initialize Supabase client:', err)
    return {
      provide: {
        supabase: null
      }
    }
  }
})
