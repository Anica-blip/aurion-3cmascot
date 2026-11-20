-- Repo path: supabase/migrations/20261120_about_3c_table.sql
-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn). Already applied on 2026-11-20 (migration name: about_3c_table).
-- Table for the briefing the Aurion bot AI reads with every /ask that has no FAQ or keyword answer.
-- Content is written by Chief in the Drive sheet tab "about_3c" and loaded here (14 rows on 2026-11-20).
-- RLS on, NO policies on purpose: only the Worker's service key reads it (same pattern as greeted_users).

create table if not exists public.about_3c (
  id integer primary key,
  topic text not null,
  info text not null,
  link text
);

alter table public.about_3c enable row level security;
revoke all on public.about_3c from anon, authenticated;

comment on table public.about_3c is 'Briefing for the Aurion bot AI (/ask). Written by Chief in the Drive sheet tab about_3c. Read by the aurion-bot Worker with the service key only.';
