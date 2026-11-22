-- ROLLBACK for 20261121_drop_pg_cron_pg_net.sql
-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn)
-- Before: pg_cron 1.6 (schema pg_catalog), pg_net 0.14.0 (schema public). Old run history and queue were empty/cleared.
-- If pg_cron fails to create from SQL, enable it under Database > Extensions in the dashboard.

CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA public;
