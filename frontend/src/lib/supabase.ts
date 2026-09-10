import { createClient } from '@supabase/supabase-js'
import { z } from 'zod'

const Env = z.object({
  VITE_SUPABASE_URL: z.string().url(),
  VITE_SUPABASE_ANON_KEY: z.string().min(10),
  VITE_API_URL: z.string().url(),
})
export const env = Env.parse(import.meta.env)
export const supabase = createClient(env.VITE_SUPABASE_URL, env.VITE_SUPABASE_ANON_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
})
