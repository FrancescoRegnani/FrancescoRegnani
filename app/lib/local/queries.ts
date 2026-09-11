// Demo-mode implementation of lib/remote-queries.ts's public API, backed by
// on-device AsyncStorage instead of Supabase. Same function signatures so
// lib/queries.ts can switch between the two transparently.
import {
  approximateReadiness,
  clampMastery,
  daysBetween,
  masteryDelta,
  nextReviewIntervalDays,
  nextStreak,
  toDateOnlyISO,
  xpForLessonCompletion,
} from '../learning';
import type { Exam, Lesson, Question, Subject, Unit, UserProfile, UserProgress } from '../types';
import * as content from './content';
import * as store from './store';
import type { LocalErrorRow } from './store';
import type {
  ErrorSummaryItem,
  LessonCompletionSummary,
  NextLessonInfo,
  QuizAnswerResult,
} from '../remote-queries';

function todayISO(): string {
  return toDateOnlyISO(new Date());
}

export async function fetchExams(): Promise<Exam[]> {
  return content.exams;
}

export async function fetchUserProfile(_userId: string): Promise<UserProfile | null> {
  return store.getProfile();
}

export async function updateUserProfile(_userId: string, patch: Partial<UserProfile>): Promise<void> {
  const current = (await store.getProfile()) ?? store.defaultProfile('', '');
  await store.saveProfile({ ...current, ...patch });
}

export async function fetchSubjectsForExam(examId: string): Promise<Subject[]> {
  return content.subjects.filter((s) => s.exam_id === examId).sort((a, b) => a.order_number - b.order_number);
}

export async function fetchUnitsForSubject(subjectId: string): Promise<Unit[]> {
  return content.units.filter((u) => u.subject_id === subjectId).sort((a, b) => a.order_number - b.order_number);
}

export async function fetchLessonsForUnit(unitId: string): Promise<Lesson[]> {
  return content.lessons.filter((l) => l.unit_id === unitId).sort((a, b) => a.order_number - b.order_number);
}

export async function fetchLesson(lessonId: string): Promise<Lesson | null> {
  return content.lessons.find((l) => l.id === lessonId) ?? null;
}

export async function fetchQuestionsForLesson(lessonId: string): Promise<Question[]> {
  return content.questions.filter((q) => q.lesson_id === lessonId && q.verified && !q.is_blind);
}

export async function fetchProgressForUser(_userId: string): Promise<Record<string, UserProgress>> {
  return store.getProgressMap();
}

export async function fetchProgressForLesson(_userId: string, lessonId: string): Promise<UserProgress | null> {
  const map = await store.getProgressMap();
  return map[lessonId] ?? null;
}

export async function fetchDueLessonIds(_userId: string): Promise<string[]> {
  const map = await store.getProgressMap();
  const today = todayISO();
  return Object.values(map)
    .filter((p) => p.next_review && p.next_review <= today)
    .map((p) => p.lesson_id);
}

export async function fetchErrorSummary(_userId: string): Promise<ErrorSummaryItem[]> {
  const errors = await store.getErrors();
  const counts = new Map<string, ErrorSummaryItem>();
  for (const err of errors) {
    if (err.resolved) continue;
    const lesson = content.lessons.find((l) => l.id === err.lessonId);
    if (!lesson) continue;
    const existing = counts.get(lesson.id);
    if (existing) existing.count += 1;
    else counts.set(lesson.id, { lessonId: lesson.id, lessonTitle: lesson.title, count: 1 });
  }
  return Array.from(counts.values());
}

export async function completeLessonSession(params: {
  userId: string;
  lessonId: string;
  answers: QuizAnswerResult[];
  previousProgress: UserProgress | null;
  profile: UserProfile;
}): Promise<LessonCompletionSummary> {
  const { lessonId, answers, previousProgress, profile } = params;
  const today = todayISO();

  const errors = await store.getErrors();
  const errorsByQuestion = new Map<string, LocalErrorRow>(errors.map((e) => [e.questionId, e]));
  for (const a of answers) {
    if (!a.correct) {
      errorsByQuestion.set(a.questionId, { questionId: a.questionId, lessonId, resolved: false });
    } else if (errorsByQuestion.has(a.questionId)) {
      errorsByQuestion.set(a.questionId, { ...errorsByQuestion.get(a.questionId)!, resolved: true });
    }
  }
  await store.saveErrors(Array.from(errorsByQuestion.values()));

  const daysSinceLastReview = previousProgress?.last_review
    ? daysBetween(previousProgress.last_review, today)
    : null;

  let mastery = previousProgress?.mastery ?? 0;
  for (const a of answers) {
    mastery = clampMastery(mastery + masteryDelta({ correct: a.correct, daysSinceLastReview, previousMastery: mastery }));
  }

  const accuracy = answers.length > 0 ? answers.filter((a) => a.correct).length / answers.length : 0;
  const currentIntervalDays =
    previousProgress?.last_review && previousProgress?.next_review
      ? daysBetween(previousProgress.last_review, previousProgress.next_review)
      : null;
  const intervalDays = nextReviewIntervalDays(accuracy >= 0.6, currentIntervalDays);
  const nextReviewDate = new Date();
  nextReviewDate.setDate(nextReviewDate.getDate() + intervalDays);

  const progressMap = await store.getProgressMap();
  progressMap[lessonId] = {
    user_id: store.DEMO_USER_ID,
    lesson_id: lessonId,
    completed: true,
    accuracy,
    mastery,
    last_review: today,
    next_review: toDateOnlyISO(nextReviewDate),
    attempts: (previousProgress?.attempts ?? 0) + 1,
  };
  await store.saveProgressMap(progressMap);

  const xpEarned = xpForLessonCompletion(accuracy);
  const newStreak = nextStreak(profile.current_streak, profile.last_study_date, today);

  const totalTimeSeconds = answers.reduce((sum, a) => sum + a.responseTimeSeconds, 0);
  await store.addMinutesStudiedToday(today, totalTimeSeconds / 60);

  await updateUserProfile(store.DEMO_USER_ID, {
    xp: profile.xp + xpEarned,
    current_streak: newStreak,
    last_study_date: today,
  });

  return { xpEarned, accuracy, mastery, newStreak, totalTimeSeconds };
}

export async function fetchMinutesStudiedToday(_userId: string): Promise<number> {
  return Math.round(await store.getMinutesStudiedToday(todayISO()));
}

export async function fetchNextLesson(_userId: string, examId: string): Promise<NextLessonInfo | null> {
  const subjects = await fetchSubjectsForExam(examId);
  const progress = await store.getProgressMap();

  for (const subject of subjects) {
    const units = await fetchUnitsForSubject(subject.id);
    for (const unit of units) {
      const lessons = await fetchLessonsForUnit(unit.id);
      const next = lessons.find((l) => !progress[l.id]?.completed);
      if (next) return { lesson: next, unit, subject };
    }
  }
  return null;
}

export async function computeUnitReadiness(_userId: string, unitId: string): Promise<number> {
  const lessons = await fetchLessonsForUnit(unitId);
  if (lessons.length === 0) return 0;
  const progress = await store.getProgressMap();
  const masteries = lessons.map((l) => progress[l.id]?.mastery ?? 0);
  const completedCount = lessons.filter((l) => progress[l.id]?.completed).length;
  const averageMastery = masteries.reduce((a, b) => a + b, 0) / masteries.length;
  const coverageRatio = completedCount / lessons.length;
  return approximateReadiness({ averageMastery, coverageRatio });
}
