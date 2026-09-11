import AsyncStorage from '@react-native-async-storage/async-storage';
import type { UserProfile, UserProgress } from '../types';

const KEY_PREFIX = 'proexam_demo_v1_';
const PROFILE_KEY = `${KEY_PREFIX}profile`;
const LOGGED_IN_KEY = `${KEY_PREFIX}logged_in`;
const PROGRESS_KEY = `${KEY_PREFIX}progress`;
const ERRORS_KEY = `${KEY_PREFIX}errors`;
const MINUTES_TODAY_KEY = `${KEY_PREFIX}minutes_today`;

export const DEMO_USER_ID = 'demo-user';

async function readJSON<T>(key: string): Promise<T | null> {
  const raw = await AsyncStorage.getItem(key);
  return raw ? (JSON.parse(raw) as T) : null;
}

async function writeJSON(key: string, value: unknown): Promise<void> {
  await AsyncStorage.setItem(key, JSON.stringify(value));
}

export function defaultProfile(name: string, email: string): UserProfile {
  return {
    id: DEMO_USER_ID,
    name,
    email,
    selected_exam: null,
    exam_date: null,
    daily_minutes: 15,
    xp: 0,
    current_streak: 0,
    last_study_date: null,
    readiness_score: 0,
    created_at: new Date().toISOString(),
  };
}

export async function getProfile(): Promise<UserProfile | null> {
  return readJSON<UserProfile>(PROFILE_KEY);
}

export async function saveProfile(profile: UserProfile): Promise<void> {
  await writeJSON(PROFILE_KEY, profile);
}

export async function isLoggedIn(): Promise<boolean> {
  return (await AsyncStorage.getItem(LOGGED_IN_KEY)) === 'true';
}

export async function setLoggedIn(value: boolean): Promise<void> {
  await AsyncStorage.setItem(LOGGED_IN_KEY, value ? 'true' : 'false');
}

export async function getProgressMap(): Promise<Record<string, UserProgress>> {
  return (await readJSON<Record<string, UserProgress>>(PROGRESS_KEY)) ?? {};
}

export async function saveProgressMap(map: Record<string, UserProgress>): Promise<void> {
  await writeJSON(PROGRESS_KEY, map);
}

export interface LocalErrorRow {
  questionId: string;
  lessonId: string;
  resolved: boolean;
}

export async function getErrors(): Promise<LocalErrorRow[]> {
  return (await readJSON<LocalErrorRow[]>(ERRORS_KEY)) ?? [];
}

export async function saveErrors(rows: LocalErrorRow[]): Promise<void> {
  await writeJSON(ERRORS_KEY, rows);
}

export async function getMinutesStudiedToday(todayISO: string): Promise<number> {
  const stored = await readJSON<{ date: string; minutes: number }>(MINUTES_TODAY_KEY);
  if (!stored || stored.date !== todayISO) return 0;
  return stored.minutes;
}

export async function addMinutesStudiedToday(todayISO: string, minutesToAdd: number): Promise<void> {
  const current = await getMinutesStudiedToday(todayISO);
  await writeJSON(MINUTES_TODAY_KEY, { date: todayISO, minutes: current + minutesToAdd });
}

/** Wipes all local demo data (used only for a future "reset demo" action). */
export async function clearAll(): Promise<void> {
  await AsyncStorage.multiRemove([PROFILE_KEY, LOGGED_IN_KEY, PROGRESS_KEY, ERRORS_KEY, MINUTES_TODAY_KEY]);
}
