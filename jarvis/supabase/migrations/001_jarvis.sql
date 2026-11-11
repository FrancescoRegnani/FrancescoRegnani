-- Jarvis: memoria a lungo termine e cronologia breve della conversazione.
-- Le tabelle sono accessibili SOLO dalla Edge Function (service role):
-- RLS attiva e nessuna policy = nessun accesso dalle chiavi pubbliche.

create table if not exists public.jarvis_memories (
  id bigint generated always as identity primary key,
  content text not null check (char_length(content) between 1 and 1000),
  created_at timestamptz not null default now()
);

create table if not exists public.jarvis_messages (
  id bigint generated always as identity primary key,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists jarvis_messages_created_at_idx
  on public.jarvis_messages (created_at desc);

alter table public.jarvis_memories enable row level security;
alter table public.jarvis_messages enable row level security;
