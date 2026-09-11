// When no Supabase project is configured, the app runs in local "demo mode":
// a single offline profile stored on-device with AsyncStorage instead of a
// real backend. This lets you try ProExam in Expo Go with zero accounts.
// As soon as .env has real Supabase credentials, the app switches to the
// real backend automatically — no code changes needed.
export const isDemoMode = !process.env.EXPO_PUBLIC_SUPABASE_URL || !process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;
