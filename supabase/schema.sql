-- ProExam database schema (MVP)
-- Run this once in the Supabase SQL editor of a fresh project.
-- Matches PROEXAM_GUIDE.md, Fase 6 and Fase 7.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Content tables (read-only for regular users, written by admins/seed scripts)
-- ---------------------------------------------------------------------------

create table if not exists public.exams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  icon text,
  color_primary text,
  color_secondary text,
  active boolean not null default true,
  order_number integer not null default 0
);

create table if not exists public.subjects (
  id uuid primary key default gen_random_uuid(),
  exam_id uuid not null references public.exams (id) on delete cascade,
  name text not null,
  description text,
  order_number integer not null default 0
);

create table if not exists public.units (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null references public.subjects (id) on delete cascade,
  title text not null,
  description text,
  order_number integer not null default 0
);

create table if not exists public.lessons (
  id uuid primary key default gen_random_uuid(),
  unit_id uuid not null references public.units (id) on delete cascade,
  title text not null,
  explanation text,
  difficulty integer not null default 1,
  xp_reward integer not null default 20,
  order_number integer not null default 0,
  is_checkpoint boolean not null default false
);

create table if not exists public.questions (
  id uuid primary key default gen_random_uuid(),
  lesson_id uuid not null references public.lessons (id) on delete cascade,
  question text not null,
  answer_a text,
  answer_b text,
  answer_c text,
  answer_d text,
  correct_answer text not null,
  explanation text,
  difficulty integer not null default 1,
  source text,
  source_date date,
  verified boolean not null default false,
  question_type text not null default 'multiple_choice'
    check (question_type in ('multiple_choice', 'true_false', 'open', 'numeric', 'case')),
  is_blind boolean not null default false
);

-- ---------------------------------------------------------------------------
-- User tables
-- ---------------------------------------------------------------------------

create table if not exists public.users (
  id uuid primary key references auth.users (id) on delete cascade,
  name text,
  email text,
  selected_exam uuid references public.exams (id),
  exam_date date,
  daily_minutes integer not null default 15,
  xp integer not null default 0,
  current_streak integer not null default 0,
  last_study_date date,
  readiness_score numeric not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.user_answers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  question_id uuid not null references public.questions (id) on delete cascade,
  answer text not null,
  correct boolean not null,
  response_time integer,
  created_at timestamptz not null default now()
);

create table if not exists public.user_progress (
  user_id uuid not null references public.users (id) on delete cascade,
  lesson_id uuid not null references public.lessons (id) on delete cascade,
  completed boolean not null default false,
  accuracy numeric,
  mastery numeric not null default 0,
  last_review date,
  next_review date,
  attempts integer not null default 0,
  primary key (user_id, lesson_id)
);

create table if not exists public.errors (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  question_id uuid not null references public.questions (id) on delete cascade,
  error_type text,
  created_at timestamptz not null default now(),
  resolved boolean not null default false
);

-- ---------------------------------------------------------------------------
-- Auto-create a public.users row whenever someone signs up via Supabase Auth
-- ---------------------------------------------------------------------------

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.users (id, email, name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data ->> 'name', ''))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------

alter table public.exams enable row level security;
alter table public.subjects enable row level security;
alter table public.units enable row level security;
alter table public.lessons enable row level security;
alter table public.questions enable row level security;
alter table public.users enable row level security;
alter table public.user_answers enable row level security;
alter table public.user_progress enable row level security;
alter table public.errors enable row level security;

-- Content: any authenticated user can read; only the service role (admin
-- tooling / seed scripts) can write, since no insert/update/delete policy
-- is defined for the authenticated role.
create policy "Authenticated users can read exams" on public.exams
  for select to authenticated using (active = true);

create policy "Authenticated users can read subjects" on public.subjects
  for select to authenticated using (true);

create policy "Authenticated users can read units" on public.units
  for select to authenticated using (true);

create policy "Authenticated users can read lessons" on public.lessons
  for select to authenticated using (true);

create policy "Authenticated users can read verified questions" on public.questions
  for select to authenticated using (verified = true);

-- users: everyone can only see/edit their own row.
create policy "Users can view own profile" on public.users
  for select to authenticated using (auth.uid() = id);

create policy "Users can update own profile" on public.users
  for update to authenticated using (auth.uid() = id) with check (auth.uid() = id);

-- user_answers: own rows only.
create policy "Users can view own answers" on public.user_answers
  for select to authenticated using (auth.uid() = user_id);

create policy "Users can insert own answers" on public.user_answers
  for insert to authenticated with check (auth.uid() = user_id);

-- user_progress: own rows only.
create policy "Users can view own progress" on public.user_progress
  for select to authenticated using (auth.uid() = user_id);

create policy "Users can insert own progress" on public.user_progress
  for insert to authenticated with check (auth.uid() = user_id);

create policy "Users can update own progress" on public.user_progress
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- errors: own rows only.
create policy "Users can view own errors" on public.errors
  for select to authenticated using (auth.uid() = user_id);

create policy "Users can insert own errors" on public.errors
  for insert to authenticated with check (auth.uid() = user_id);

create policy "Users can update own errors" on public.errors
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
