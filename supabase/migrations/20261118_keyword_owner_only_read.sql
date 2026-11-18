-- Repo path: supabase/migrations/20261118_keyword_owner_only_read.sql
-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn)  | ALREADY APPLIED 2026-11-18
-- Purpose: keyword answers are no longer readable by the public anon key.
-- The Aurion Worker reads with the service key, which ignores RLS.
drop policy if exists "Allow read to everyone" on public.keyword;
create policy "Owner can read keyword" on public.keyword
  for select to authenticated using ((select public.is_owner()));
