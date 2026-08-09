import { createClient } from '@supabase/supabase-js'

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()

  const supabaseUrl = config.public.supabaseUrl
  const supabaseKey = config.public.supabaseKey

  if (!supabaseUrl || !supabaseKey) {
    console.warn(
      'Supabase environment variables (SUPABASE_URL and SUPABASE_KEY) are missing. ' +
      'Realtime subscriptions and frontend calls will fail until configured.'
    );
  }

  // Create the client
  const supabase = createClient(supabaseUrl, supabaseKey)

  return {
    provide: {
      supabase
    }
  }
})
