// Pure scoring functions for XP, mastery, spaced repetition and streaks.
// Deliberately simple first versions per PROEXAM_GUIDE.md Fase 14-19 and 25;
// the guide itself says to replace these with a more sophisticated model
// later, once the MVP loop works end to end.

export const XP_PER_CORRECT_ANSWER = 10;
export const XP_PER_LESSON_COMPLETE = 20;
export const XP_PERFECT_LESSON_BONUS = 20;

export function xpForAnswer(correct: boolean): number {
  return correct ? XP_PER_CORRECT_ANSWER : 0;
}

export function xpForLessonCompletion(accuracy: number): number {
  const perfect = accuracy >= 1;
  return XP_PER_LESSON_COMPLETE + (perfect ? XP_PERFECT_LESSON_BONUS : 0);
}

const MASTERY_HIGH_THRESHOLD = 80;

/** Fase 15: mastery moves by a small fixed amount per answer. */
export function masteryDelta(params: {
  correct: boolean;
  daysSinceLastReview: number | null;
  previousMastery: number;
}): number {
  const { correct, daysSinceLastReview, previousMastery } = params;
  if (!correct) {
    return previousMastery >= MASTERY_HIGH_THRESHOLD ? -5 : -3;
  }
  if (daysSinceLastReview !== null && daysSinceLastReview >= 30) return 8;
  if (daysSinceLastReview !== null && daysSinceLastReview >= 7) return 6;
  return 4;
}

export function clampMastery(value: number): number {
  return Math.max(0, Math.min(100, value));
}

/** Fase 16: spaced repetition ladder, in days. */
export const REVIEW_INTERVAL_LADDER_DAYS = [1, 3, 7, 14, 30, 60] as const;

export function nextReviewIntervalDays(correct: boolean, currentIntervalDays: number | null): number {
  if (!correct) return REVIEW_INTERVAL_LADDER_DAYS[0];
  const ladder = REVIEW_INTERVAL_LADDER_DAYS;
  const currentIndex = currentIntervalDays === null ? -1 : ladder.indexOf(currentIntervalDays as (typeof ladder)[number]);
  const nextIndex = currentIndex === -1 ? 1 : Math.min(currentIndex + 1, ladder.length - 1);
  return ladder[nextIndex];
}

export function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

export function daysBetween(fromISO: string, toISO: string): number {
  const from = new Date(fromISO + 'T00:00:00Z').getTime();
  const to = new Date(toISO + 'T00:00:00Z').getTime();
  return Math.round((to - from) / (1000 * 60 * 60 * 24));
}

export function toDateOnlyISO(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Fase 19: streak counting. */
export function nextStreak(currentStreak: number, lastStudyDateISO: string | null, todayISO: string): number {
  if (!lastStudyDateISO) return 1;
  const diff = daysBetween(lastStudyDateISO, todayISO);
  if (diff <= 0) return Math.max(currentStreak, 1);
  if (diff === 1) return currentStreak + 1;
  return 1;
}

/**
 * Fase 25: Readiness Score. The full formula (30% mastery, 20% retention,
 * 15% coverage, 20% simulations, 15% recent quiz) needs retention tracking
 * and simulations, which ship after the MVP (Fase 21-31). Until then this
 * approximates readiness from mastery and coverage alone so the Home screen
 * has something meaningful to show.
 */
export function approximateReadiness(params: { averageMastery: number; coverageRatio: number }): number {
  const { averageMastery, coverageRatio } = params;
  const score = averageMastery * 0.6 + coverageRatio * 100 * 0.4;
  return Math.round(Math.max(0, Math.min(100, score)));
}

export function daysUntil(examDateISO: string | null, todayISO: string): number | null {
  if (!examDateISO) return null;
  return daysBetween(todayISO, examDateISO);
}
