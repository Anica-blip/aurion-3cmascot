-- Repo path: supabase/migrations/rollback/20261120_about_3c_table_ROLLBACK.sql
-- Undoes 20261120_about_3c_table.sql: removes the table and its 14 rows.
-- The content is kept in Chief's Drive sheet (tab about_3c), so it can be loaded again.
-- If you roll back, also put the previous worker.js back first, or /ask will answer without the briefing.

drop table if exists public.about_3c;
