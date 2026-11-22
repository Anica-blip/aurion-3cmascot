-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn)
-- Removes the pg_cron and pg_net extensions left over from the first cron-runner attempt (cancelled).
-- Checked first: 0 pg_cron jobs, 0 queued pg_net requests, no function uses net.http_* or cron.*.
-- Rollback: 20261121_drop_pg_cron_pg_net_ROLLBACK.sql

DROP EXTENSION IF EXISTS pg_cron;
DROP EXTENSION IF EXISTS pg_net;
