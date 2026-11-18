-- Repo path: supabase/migrations/rollback/20261118_keyword_owner_only_read_ROLLBACK.sql
-- Restores the previous public read policy.
drop policy if exists "Owner can read keyword" on public.keyword;
create policy "Allow read to everyone" on public.keyword
  for select to public using (true);
