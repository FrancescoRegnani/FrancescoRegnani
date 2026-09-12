import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ACCENT_PALETTE, DEFAULT_ACCENT_KEY, type AccentColor } from '../constants/theme';

const STORAGE_KEY = 'proexam_accent_color';

function findAccent(key: string | null): AccentColor {
  return ACCENT_PALETTE.find((a) => a.key === key) ?? ACCENT_PALETTE[0];
}

interface AccentContextValue {
  accent: AccentColor;
  setAccentKey: (key: string) => void;
}

const AccentContext = createContext<AccentContextValue>({
  accent: findAccent(DEFAULT_ACCENT_KEY),
  setAccentKey: () => {},
});

// Personal appearance preference: this is a per-device UI choice, not exam
// content, so it lives in AsyncStorage directly rather than the user
// profile — it applies the same way whether the app is in demo mode or
// talking to a real Supabase project.
export function AccentProvider({ children }: { children: ReactNode }) {
  const [accent, setAccent] = useState<AccentColor>(findAccent(DEFAULT_ACCENT_KEY));

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((stored) => {
      if (stored) setAccent(findAccent(stored));
    });
  }, []);

  function setAccentKey(key: string) {
    setAccent(findAccent(key));
    AsyncStorage.setItem(STORAGE_KEY, key);
  }

  return <AccentContext.Provider value={{ accent, setAccentKey }}>{children}</AccentContext.Provider>;
}

export function useAccent(): AccentContextValue {
  return useContext(AccentContext);
}
