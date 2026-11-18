-- Repo path: supabase/migrations/20261118_greeted_users_unique_telegram_user_id.sql
-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn)  | ALREADY APPLIED 2026-11-18
-- Purpose: lets the Aurion Worker record a greeted user once, never twice.
create unique index if not exists greeted_users_telegram_user_id_key
  on public.greeted_users (telegram_user_id);
