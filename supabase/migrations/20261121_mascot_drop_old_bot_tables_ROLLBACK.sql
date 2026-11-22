-- ROLLBACK for 20261121_mascot_drop_old_bot_tables.sql
-- Project: Aurion 3C Mascot (cgxjqsbrditbteqhdyus)
-- Recreates the empty structure only (primary keys assumed on id). Rows: see project doc
-- aurion-mascot-old-bot-tables-backup-2026-11-18.md (faq, fact, keyword) and
-- aurion-mascot-old-bot-tables-backup-2026-11-21.md (message).
-- RLS was enabled on greeted_users with no policies; re-run the security advisor after restoring.

CREATE SCHEMA IF NOT EXISTS "Telegram bot";

CREATE TABLE "Telegram bot".faq (
  id bigint NOT NULL PRIMARY KEY,
  question text,
  answer text
);

CREATE TABLE "Telegram bot".fact (
  id bigint NOT NULL PRIMARY KEY,
  fact text
);

CREATE TABLE "Telegram bot".keyword (
  id bigint NOT NULL PRIMARY KEY,
  keyword text NOT NULL,
  answer text NOT NULL
);

CREATE TABLE "Telegram bot".greeted_users (
  id bigint NOT NULL PRIMARY KEY,
  "1377419565" bigint,
  greeted_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE "Telegram bot".greeted_users ENABLE ROW LEVEL SECURITY;

CREATE TABLE "Telegram bot".message (
  id bigint NOT NULL PRIMARY KEY,
  content text,
  frequency text,
  group_channel text,
  title jsonb,
  notes text,
  scheduled_at timestamptz DEFAULT now(),
  sent boolean DEFAULT false,
  thread_id text
);
