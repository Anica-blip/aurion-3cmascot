-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn)
-- Removes five database functions left over from the first cron-runner attempt (cancelled).
-- Checked first: not called by the repo, by any other database function, or by any trigger.
-- Rollback: 20261121_drop_old_cron_runner_functions_ROLLBACK.sql

DROP FUNCTION IF EXISTS public.comprehensive_scheduled_posts_check();
DROP FUNCTION IF EXISTS public.log_post_attempt(text, text, text, timestamp with time zone);
DROP FUNCTION IF EXISTS public.move_sent_posts_to_dashboard();
DROP FUNCTION IF EXISTS public.retry_failed_posts(integer);
DROP FUNCTION IF EXISTS public.runner_mark_attempt(uuid, text, boolean, integer, text, text, text, text);
