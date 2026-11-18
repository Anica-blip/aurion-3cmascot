-- Repo path: supabase/migrations/rollback/20261118_greeted_users_unique_telegram_user_id_ROLLBACK.sql
drop index if exists public.greeted_users_telegram_user_id_key;
