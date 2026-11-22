-- Project: Aurion 3C Mascot (cgxjqsbrditbteqhdyus)
-- Removes the five old Telegram bot tables in schema "Telegram bot". The live bot uses 3C Control Center.
-- Checked first: no foreign keys, views or functions reference them; Mascot Postgres already on 17.12.
-- Backup of the only table with unique data (message): project doc aurion-mascot-old-bot-tables-backup-2026-11-21.md
-- Rollback: 20261121_mascot_drop_old_bot_tables_ROLLBACK.sql (structure only; rows are in the backup doc)

DROP TABLE IF EXISTS "Telegram bot".faq;
DROP TABLE IF EXISTS "Telegram bot".fact;
DROP TABLE IF EXISTS "Telegram bot".keyword;
DROP TABLE IF EXISTS "Telegram bot".greeted_users;
DROP TABLE IF EXISTS "Telegram bot".message;
