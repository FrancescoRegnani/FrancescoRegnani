-- Jarvis: registro dei consumi, per rispettare il budget mensile.
-- Una riga per ogni chiamata all'API di Claude, con il costo stimato in dollari.

create table if not exists public.jarvis_usage (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  model text not null,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  cache_read_tokens integer not null default 0,
  cache_write_tokens integer not null default 0,
  web_searches integer not null default 0,
  cost_usd numeric(10, 6) not null default 0
);

create index if not exists jarvis_usage_created_at_idx
  on public.jarvis_usage (created_at desc);

alter table public.jarvis_usage enable row level security;
