import { supabase } from './supabase';
import {
  approximateReadiness,
  daysBetween,
  masteryDelta,
  clampMastery,
  nextReviewIntervalDays,
  nextStreak,
  toDateOnlyISO,
  xpForLessonCompletion,
} from './learning';
import type { Exam, Lesson, Question, Subject, Unit, UserProfile, UserProgress } from './types';

function todayISO(): string {
  return toDateOnlyISO(new Date());
}

export async function fetchExams(): Promise<Exam[]> {
  const { data, error } = await supabase.from('exams').select('*').order('order_number');
  if (error) throw error;
  return data ?? [];
}

export async function fetchUserProfile(userId: string): Promise<UserProfile | null> {
  const { data, error } = await supabase.from('users').select('*').eq('id', userId).maybeSingle();
  if (error) throw error;
  return data;
}

export async function updateUserProfile(userId: string, patch: Partial<UserProfile>): Promise<void> {
  const { error } = await supabase.from('users').update(patch).eq('id', userId);
  if (error) throw error;
}

export async function fetchSubjectsForExam(examId: string): Promise<Subject[]> {
  const { data, error } = await supabase
    .from('subjects')
    .select('*')
    .eq('exam_id', examId)
    .order('order_number');
  if (error) throw error;
  return data ?? [];
}

export async function fetchUnitsForSubject(subjectId: string): Promise<Unit[]> {
  const { data, error } = await supabase
    .from('units')
    .select('*')
    .eq('subject_id', subjectId)
    .order('order_number');
  if (error) throw error;
  return data ?? [];
}

export async function fetchLessonsForUnit(unitId: string): Promise<Lesson[]> {
  const { data, error } = await supabase
    .from('lessons')
    .select('*')
    .eq('unit_id', unitId)
    .order('order_number');
  if (error) throw error;
  return data ?? [];
}

export async function fetchLesson(lessonId: string): Promise<Lesson | null> {
  const { data, error } = await supabase.from('lessons').select('*').eq('id', lessonId).maybeSingle();
  if (error) throw error;
  return data;
}

export async function fetchQuestionsForLesson(lessonId: string): Promise<Question[]> {
  const { data, error } = await supabase
    .from('questions')
    .select('*')
    .eq('lesson_id', lessonId)
    .eq('verified', true)
    .eq('is_blind', false);
  if (error) throw error;
  return data ?? [];
}

export async function fetchProgressForUser(userId: string): Promise<Record<string, UserProgress>> {
  const { data, error } = await supabase.from('user_progress').select('*').eq('user_id', userId);
  if (error) throw error;
  const map: Record<string, UserProgress> = {};
  for (const row of data ?? []) map[row.lesson_id] = row;
  return map;
}

export async function fetchProgressForLesson(userId: string, lessonId: string): Promise<UserProgress | null> {
  const { data, error } = await supabase
    .from('user_progress')
    .select('*')
    .eq('user_id', userId)
    .eq('lesson_id', lessonId)
    .maybeSingle();
  if (error) throw error;
  return data;
}

export async function fetchDueLessonIds(userId: string): Promise<string[]> {
  const { data, error } = await supabase
    .from('user_progress')
    .select('lesson_id, next_review')
    .eq('user_id', userId)
    .lte('next_review', todayISO());
  if (error) throw error;
  return (data ?? []).map((row) => row.lesson_id);
}

export interface ErrorSummaryItem {
  lessonId: string;
  lessonTitle: string;
  count: number;
}

/** Fase 18: group unresolved errors by lesson for the "quaderno degli errori". */
export async function fetchErrorSummary(userId: string): Promise<ErrorSummaryItem[]> {
  const { data, error } = await supabase
    .from('errors')
    .select('question_id, questions(lesson_id, lessons(id, title))')
    .eq('user_id', userId)
    .eq('resolved', false);
  if (error) throw error;

  const counts = new Map<string, ErrorSummaryItem>();
  for (const row of (data ?? []) as any[]) {
    const lesson = row.questions?.lessons;
    if (!lesson) continue;
    const existing = counts.get(lesson.id);
    if (existing) existing.count += 1;
    else counts.set(lesson.id, { lessonId: lesson.id, lessonTitle: lesson.title, count: 1 });
  }
  return Array.from(counts.values());
}

export interface QuizAnswerResult {
  questionId: string;
  correct: boolean;
  responseTimeSeconds: number;
}

export interface LessonCompletionSummary {
  xpEarned: number;
  accuracy: number;
  mastery: number;
  newStreak: number;
  totalTimeSeconds: number;
}

/**
 * Fase 13-19: persist the outcome of a finished lesson/quiz session and
 * return the numbers the result screen needs. Records each answer, files
 * wrong ones as errors (and resolves previously-logged errors that were
 * just answered correctly), updates mastery + spaced repetition on
 * user_progress, and updates XP/streak on the user profile.
 */
export async function completeLessonSession(params: {
  userId: string;
  lessonId: string;
  answers: QuizAnswerResult[];
  previousProgress: UserProgress | null;
  profile: UserProfile;
}): Promise<LessonCompletionSummary> {
  const { userId, lessonId, answers, previousProgress, profile } = params;
  const today = todayISO();

  const answerRows = answers.map((a) => ({
    user_id: userId,
    question_id: a.questionId,
    answer: a.correct ? 'correct' : 'incorrect',
    correct: a.correct,
    response_time: Math.round(a.responseTimeSeconds),
  }));
  if (answerRows.length > 0) {
    const { error } = await supabase.from('user_answers').insert(answerRows);
    if (error) throw error;
  }

  const wrongQuestionIds = answers.filter((a) => !a.correct).map((a) => a.questionId);
  if (wrongQuestionIds.length > 0) {
    const { error } = await supabase.from('errors').insert(
      wrongQuestionIds.map((questionId) => ({ user_id: userId, question_id: questionId, error_type: 'quiz' }))
    );
    if (error) throw error;
  }

  const correctQuestionIds = answers.filter((a) => a.correct).map((a) => a.questionId);
  if (correctQuestionIds.length > 0) {
    const { error } = await supabase
      .from('errors')
      .update({ resolved: true })
      .eq('user_id', userId)
      .in('question_id', correctQuestionIds);
    if (error) throw error;
  }

  const daysSinceLastReview = previousProgress?.last_review
    ? daysBetween(previousProgress.last_review, today)
    : null;

  let mastery = previousProgress?.mastery ?? 0;
  for (const a of answers) {
    mastery = clampMastery(mastery + masteryDelta({ correct: a.correct, daysSinceLastReview, previousMastery: mastery }));
  }

  const accuracy = answers.length > 0 ? answers.filter((a) => a.correct).length / answers.length : 0;
  const currentIntervalDays = previousProgress?.last_review && previousProgress?.next_review
    ? daysBetween(previousProgress.last_review, previousProgress.next_review)
    : null;
  const intervalDays = nextReviewIntervalDays(accuracy >= 0.6, currentIntervalDays);
  const nextReviewDate = new Date();
  nextReviewDate.setDate(nextReviewDate.getDate() + intervalDays);

  const { error: progressError } = await supabase.from('user_progress').upsert(
    {
      user_id: userId,
      lesson_id: lessonId,
      completed: true,
      accuracy,
      mastery,
      last_review: today,
      next_review: toDateOnlyISO(nextReviewDate),
      attempts: (previousProgress?.attempts ?? 0) + 1,
    },
    { onConflict: 'user_id,lesson_id' }
  );
  if (progressError) throw progressError;

  const xpEarned = xpForLessonCompletion(accuracy);
  const newStreak = nextStreak(profile.current_streak, profile.last_study_date, today);

  const { error: userError } = await supabase
    .from('users')
    .update({
      xp: profile.xp + xpEarned,
      current_streak: newStreak,
      last_study_date: today,
    })
    .eq('id', userId);
  if (userError) throw userError;

  const totalTimeSeconds = answers.reduce((sum, a) => sum + a.responseTimeSeconds, 0);

  return { xpEarned, accuracy, mastery, newStreak, totalTimeSeconds };
}

export async function fetchMinutesStudiedToday(userId: string): Promise<number> {
  const start = `${todayISO()}T00:00:00.000Z`;
  const { data, error } = await supabase
    .from('user_answers')
    .select('response_time')
    .eq('user_id', userId)
    .gte('created_at', start);
  if (error) throw error;
  const totalSeconds = (data ?? []).reduce((sum, row) => sum + (row.response_time ?? 0), 0);
  return Math.round(totalSeconds / 60);
}

export interface NextLessonInfo {
  lesson: Lesson;
  unit: Unit;
  subject: Subject;
}

/** Fase 11: find the first not-yet-completed lesson in the user's exam path. */
export async function fetchNextLesson(userId: string, examId: string): Promise<NextLessonInfo | null> {
  const subjects = await fetchSubjectsForExam(examId);
  const progress = await fetchProgressForUser(userId);

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

/** Fase 25 (approximated for the MVP): average mastery x coverage across a unit's lessons. */
export async function computeUnitReadiness(userId: string, unitId: string): Promise<number> {
  const lessons = await fetchLessonsForUnit(unitId);
  if (lessons.length === 0) return 0;
  const progress = await fetchProgressForUser(userId);
  const masteries = lessons.map((l) => progress[l.id]?.mastery ?? 0);
  const completedCount = lessons.filter((l) => progress[l.id]?.completed).length;
  const averageMastery = masteries.reduce((a, b) => a + b, 0) / masteries.length;
  const coverageRatio = completedCount / lessons.length;
  return approximateReadiness({ averageMastery, coverageRatio });
}
