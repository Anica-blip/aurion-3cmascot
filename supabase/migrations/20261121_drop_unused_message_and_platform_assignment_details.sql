-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn)
-- Removes two empty, unused tables created by Supabase AI early on:
--   public.message                      (copy of the old bot's message table; 0 rows)
--   public.platform_assignment_details  (mirror of dashboard_platform_assignments, linked to scheduled_posts; 0 rows)
-- Checked first: no code, function, view or trigger references them; no data to back up.
-- Rollback: 20261121_drop_unused_message_and_platform_assignment_details_ROLLBACK.sql (structure only)

DROP TABLE IF EXISTS public.message;
DROP TABLE IF EXISTS public.platform_assignment_details;
