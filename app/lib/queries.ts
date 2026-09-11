// Public data-access API used by the app's screens. Transparently routes to
// the local AsyncStorage-backed implementation in demo mode, or to Supabase
// otherwise — see lib/backend-mode.ts.
import { isDemoMode } from './backend-mode';
import * as local from './local/queries';
import * as remote from './remote-queries';

const impl = isDemoMode ? local : remote;

export const fetchExams = impl.fetchExams;
export const fetchUserProfile = impl.fetchUserProfile;
export const updateUserProfile = impl.updateUserProfile;
export const fetchSubjectsForExam = impl.fetchSubjectsForExam;
export const fetchUnitsForSubject = impl.fetchUnitsForSubject;
export const fetchLessonsForUnit = impl.fetchLessonsForUnit;
export const fetchLesson = impl.fetchLesson;
export const fetchQuestionsForLesson = impl.fetchQuestionsForLesson;
export const fetchProgressForUser = impl.fetchProgressForUser;
export const fetchProgressForLesson = impl.fetchProgressForLesson;
export const fetchDueLessonIds = impl.fetchDueLessonIds;
export const fetchErrorSummary = impl.fetchErrorSummary;
export const completeLessonSession = impl.completeLessonSession;
export const fetchMinutesStudiedToday = impl.fetchMinutesStudiedToday;
export const fetchNextLesson = impl.fetchNextLesson;
export const computeUnitReadiness = impl.computeUnitReadiness;

export type { ErrorSummaryItem, LessonCompletionSummary, NextLessonInfo, QuizAnswerResult } from './remote-queries';
