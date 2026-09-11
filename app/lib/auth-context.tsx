import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { isDemoMode } from './backend-mode';
import { supabase } from './supabase';
import { fetchUserProfile } from './queries';
import * as localStore from './local/store';
import type { UserProfile } from './types';

// Minimal session shape: every screen only ever reads `session.user.id`, so
// we don't need the full Supabase `Session` type here. This also lets demo
// mode (no Supabase project) provide a fake session without faking every
// field Supabase's real Session type requires.
export interface AppSession {
  user: { id: string };
}

interface AuthContextValue {
  session: AppSession | null;
  profile: UserProfile | null;
  loading: boolean;
  refreshProfile: () => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<{ needsEmailConfirmation: boolean }>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AppSession | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadProfile(userId: string) {
    const p = await fetchUserProfile(userId);
    setProfile(p);
  }

  useEffect(() => {
    let mounted = true;

    if (isDemoMode) {
      (async () => {
        const loggedIn = await localStore.isLoggedIn();
        if (!mounted) return;
        if (loggedIn) {
          setSession({ user: { id: localStore.DEMO_USER_ID } });
          await loadProfile(localStore.DEMO_USER_ID);
        }
        setLoading(false);
      })();
      return () => {
        mounted = false;
      };
    }

    supabase.auth.getSession().then(async ({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      if (data.session) await loadProfile(data.session.user.id);
      setLoading(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      setSession(newSession);
      if (newSession) {
        await loadProfile(newSession.user.id);
      } else {
        setProfile(null);
      }
    });

    return () => {
      mounted = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  async function refreshProfile() {
    if (session) await loadProfile(session.user.id);
  }

  async function signUp(email: string, password: string, name: string) {
    if (isDemoMode) {
      const profileToSave = localStore.defaultProfile(name, email);
      await localStore.saveProfile(profileToSave);
      await localStore.setLoggedIn(true);
      setSession({ user: { id: localStore.DEMO_USER_ID } });
      setProfile(profileToSave);
      return { needsEmailConfirmation: false };
    }
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { name } },
    });
    if (error) throw error;
    return { needsEmailConfirmation: !data.session };
  }

  async function signIn(email: string, password: string) {
    if (isDemoMode) {
      const existing = await localStore.getProfile();
      if (!existing) {
        throw new Error('Nessun account demo trovato su questo dispositivo. Registrati prima.');
      }
      await localStore.setLoggedIn(true);
      setSession({ user: { id: localStore.DEMO_USER_ID } });
      setProfile(existing);
      return;
    }
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }

  async function signOut() {
    if (isDemoMode) {
      await localStore.setLoggedIn(false);
      setSession(null);
      setProfile(null);
      return;
    }
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  }

  return (
    <AuthContext.Provider value={{ session, profile, loading, refreshProfile, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
