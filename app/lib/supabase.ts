import 'react-native-url-polyfill/auto';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { isDemoMode } from './backend-mode';
import type { Database } from './database.types';

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

// In demo mode (no .env configured) nothing ever calls into this client —
// see lib/queries.ts and lib/auth-context.tsx, which route to the local
// AsyncStorage-backed implementation instead. We still export a typed
// `supabase` binding so the rest of the codebase can import it unconditionally.
export const supabase: SupabaseClient<Database> = isDemoMode
  ? (null as unknown as SupabaseClient<Database>)
  : createClient<Database>(supabaseUrl as string, supabaseAnonKey as string, {
      auth: {
        storage: AsyncStorage,
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false,
      },
    });
