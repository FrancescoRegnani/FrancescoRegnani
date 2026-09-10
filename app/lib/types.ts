import type { Database } from './database.types';

export type Exam = Database['public']['Tables']['exams']['Row'];
export type Subject = Database['public']['Tables']['subjects']['Row'];
export type Unit = Database['public']['Tables']['units']['Row'];
export type Lesson = Database['public']['Tables']['lessons']['Row'];
export type Question = Database['public']['Tables']['questions']['Row'];
export type UserProfile = Database['public']['Tables']['users']['Row'];
export type UserProgress = Database['public']['Tables']['user_progress']['Row'];
export type UserAnswer = Database['public']['Tables']['user_answers']['Row'];
export type ErrorRow = Database['public']['Tables']['errors']['Row'];

export const SUPPORTED_EXAM_NAME = 'Commercialista';
