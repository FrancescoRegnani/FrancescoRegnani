// Hand-written mirror of the Supabase schema defined in supabase/schema.sql.
// If you change the schema, regenerate with the Supabase CLI instead:
//   supabase gen types typescript --project-id <id> > lib/database.types.ts

export type QuestionType = 'multiple_choice' | 'true_false' | 'open' | 'numeric' | 'case';

type NoRelationships = { Relationships: [] };

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string;
          name: string | null;
          email: string | null;
          selected_exam: string | null;
          exam_date: string | null;
          daily_minutes: number;
          xp: number;
          current_streak: number;
          last_study_date: string | null;
          readiness_score: number;
          created_at: string;
        };
        Insert: Partial<Database['public']['Tables']['users']['Row']> & { id: string };
        Update: Partial<Database['public']['Tables']['users']['Row']>;
      } & NoRelationships;
      exams: {
        Row: {
          id: string;
          name: string;
          description: string | null;
          icon: string | null;
          color_primary: string | null;
          color_secondary: string | null;
          active: boolean;
          order_number: number;
        };
        Insert: Partial<Database['public']['Tables']['exams']['Row']> & { id?: string; name: string };
        Update: Partial<Database['public']['Tables']['exams']['Row']>;
      } & NoRelationships;
      subjects: {
        Row: {
          id: string;
          exam_id: string;
          name: string;
          description: string | null;
          order_number: number;
        };
        Insert: Partial<Database['public']['Tables']['subjects']['Row']> & { id?: string; exam_id: string; name: string };
        Update: Partial<Database['public']['Tables']['subjects']['Row']>;
      } & NoRelationships;
      units: {
        Row: {
          id: string;
          subject_id: string;
          title: string;
          description: string | null;
          order_number: number;
        };
        Insert: Partial<Database['public']['Tables']['units']['Row']> & { id?: string; subject_id: string; title: string };
        Update: Partial<Database['public']['Tables']['units']['Row']>;
      } & NoRelationships;
      lessons: {
        Row: {
          id: string;
          unit_id: string;
          title: string;
          explanation: string | null;
          difficulty: number;
          xp_reward: number;
          order_number: number;
          is_checkpoint: boolean;
        };
        Insert: Partial<Database['public']['Tables']['lessons']['Row']> & { id?: string; unit_id: string; title: string };
        Update: Partial<Database['public']['Tables']['lessons']['Row']>;
      } & NoRelationships;
      questions: {
        Row: {
          id: string;
          lesson_id: string;
          question: string;
          answer_a: string | null;
          answer_b: string | null;
          answer_c: string | null;
          answer_d: string | null;
          correct_answer: string;
          explanation: string | null;
          difficulty: number;
          source: string | null;
          source_date: string | null;
          verified: boolean;
          question_type: QuestionType;
          is_blind: boolean;
        };
        Insert: Partial<Database['public']['Tables']['questions']['Row']> & {
          id?: string;
          lesson_id: string;
          question: string;
          correct_answer: string;
        };
        Update: Partial<Database['public']['Tables']['questions']['Row']>;
      } & NoRelationships;
      user_answers: {
        Row: {
          id: string;
          user_id: string;
          question_id: string;
          answer: string;
          correct: boolean;
          response_time: number | null;
          created_at: string;
        };
        Insert: Partial<Database['public']['Tables']['user_answers']['Row']> & {
          id?: string;
          user_id: string;
          question_id: string;
          answer: string;
          correct: boolean;
        };
        Update: Partial<Database['public']['Tables']['user_answers']['Row']>;
      } & NoRelationships;
      user_progress: {
        Row: {
          user_id: string;
          lesson_id: string;
          completed: boolean;
          accuracy: number | null;
          mastery: number;
          last_review: string | null;
          next_review: string | null;
          attempts: number;
        };
        Insert: Partial<Database['public']['Tables']['user_progress']['Row']> & { user_id: string; lesson_id: string };
        Update: Partial<Database['public']['Tables']['user_progress']['Row']>;
      } & NoRelationships;
      errors: {
        Row: {
          id: string;
          user_id: string;
          question_id: string;
          error_type: string | null;
          created_at: string;
          resolved: boolean;
        };
        Insert: Partial<Database['public']['Tables']['errors']['Row']> & { id?: string; user_id: string; question_id: string };
        Update: Partial<Database['public']['Tables']['errors']['Row']>;
      } & NoRelationships;
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
}
