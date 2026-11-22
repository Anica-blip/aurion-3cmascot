# SETUP — aurion-3cmascot (Aurion Bot)

> Repo path: `SETUP.md`. Names only; never a secret value in this file. Kept to the 3C Cooking Lab Standard, section G.

## 1. What it is

`aurion-3cmascot` is the Aurion Telegram bot for the 3C community. It runs as the Cloudflare Worker **`aurion-bot`**: it answers members from Supabase tables (FAQ, facts, keywords, 3C briefing), uses OpenAI when no stored answer fits, welcomes and says goodbye to members, and, on its own timer, posts the scheduled 3C posts that Chef sets up in the 3C Control Center dashboard. It moved from Render to Cloudflare on 20 Nov 2026 and got its own schedule on 22 Nov 2026.

## 2. Addresses

| What | Address |
|---|---|
| Telegram bot | The 3C Telegram community (bot name is set in BotFather) |
| Worker | The `workers.dev` address of `aurion-bot`, shown in Cloudflare → Workers & Pages → `aurion-bot`. Telegram's webhook points at `<that address>/telegram`. |
| Admin address | None. The bot has no web admin. |
| Where posts are scheduled | `https://3c-control-center.vercel.app` (the dashboard; see the `3c-control-center` repo) |

## 3. External services

| Service | What for |
|---|---|
| **Telegram** (Bot API, BotFather) | Receives and sends messages. Webhook set once with `setWebhook` (secret header and `allowed_updates` = `message`, `callback_query`). The command menu is set in BotFather (`/setcommands`). |
| **Cloudflare** | Worker `aurion-bot` and its 8 Cron Triggers. Workers Paid plan (the free plan allows only 5 Cron Triggers per account). Observability (stored logs) is **off and stays off**. |
| **Supabase**, project **3C Control Center** (`uqyqpwhkzlhqxcqajhkn`) | All the bot's tables, and `scheduled_posts` / `dashboard_posts` for the schedule. |
| **OpenAI** | Answers for `/ask` when the FAQ and keyword tables have nothing. |
| **GitHub** | This repository. No GitHub Actions are used by the bot. |

Removed on 22 Nov 2026 and no longer used: Render (bot and cron job), the Vercel cron gateway (`cron-gateway-auth`), Railway, and the old GitHub Actions posting workflow.

## 4. Supabase (project 3C Control Center)

| Table | Used for | Row Level Security and access |
|---|---|---|
| `faq` | `/faq` buttons, first answer for `/ask` | On. Public read. |
| `fact` | `/fact` | On. Public read. |
| `keyword` | Trigger words and answers | On. Owner-only read; the Worker reads it with its service key. |
| `greeted_users` | Members already welcomed (`telegram_user_id`) | On, no policy: only the service key can read or write. |
| `about_3c` | The 3C briefing the AI reads | On, no policy: only the service key can read or write. Written by Chief from the Drive sheet tab `about_3c`. |
| `scheduled_posts` | Rows with `service_type = 'aurion-bot'` and `posting_status = 'pending'`; the Worker locks, marks and removes them | Written by the Worker with the service key. |
| `dashboard_posts` | Where a sent post is recorded (`post_status`, `posting_status`, `status` = complete/sent) | Written by the Worker with the service key. |

Functions: this Worker has no owner routes, so it does not call `is_owner()`. Database changes made for this bot are in `supabase/migrations/`, each with a rollback.

## 5. Workers

**`aurion-bot`**

| Route | Access |
|---|---|
| `POST /telegram` | Private. Telegram only, with the header `X-Telegram-Bot-Api-Secret-Token`. |
| Any other method on `/telegram` | 405 |
| Everything else | 404 |
| Scheduled run (no route) | Started by Cloudflare Cron Triggers; cannot be called from outside. |

- **Deploy method:** Dashboard paste only (never Wrangler). `worker/wrangler.toml` is a record of the settings, not used to deploy.
- **Secrets (names only):** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `BOT_ADMIN_TELEGRAM_ID`. No plain variables. The Worker truly needs the service key: it reads and writes rows.
- **Cron Triggers (UTC), 8 in total:** `30 8 * * *`, `30 7 * * *`, `0 11 * * *`, `0 10 * * *`, `0 14 * * *`, `0 13 * * *`, `55 20 * * *`, `55 19 * * *`. Each Lisbon slot (08:30, 11:00, 14:00, 20:55) has one trigger for winter time and one an hour earlier for summer time. On each firing the Worker checks the real Lisbon clock and only runs if it is exactly a slot; the other trigger of the pair does nothing and logs nothing.
- **What a run does:** takes up to 20 due rows of the lane `aurion-bot`; locks each row before sending (`status = 'processing'`); converts the dashboard symbols to Telegram formatting; sends text, a picture, a video or a GIF (no documents: use a thumbnail and a link); then marks the row sent, saves it in `dashboard_posts` and removes it from `scheduled_posts`.
- **Failures:** a content problem (text over 4,096 characters, caption over 1,024, file over 45 MB or missing, Telegram refusing, more than 24 hours late) is not retried: the row stays in `scheduled_posts` marked failed with the reason in `failure_reason`, and Chef gets a Telegram message. A network or Telegram outage is retried at the next slots, up to 3 tries in total, then the same message. A row left in `processing` after its 10-minute lock is never sent again blindly: Chef is told to check Telegram first.
- **Observability:** off. Failures reach Chef by Telegram message and are saved on the row.

## 6. Login

None. Members use Telegram; admin commands and failure messages are tied to the Telegram numeric ID in `BOT_ADMIN_TELEGRAM_ID`, and fail closed if that secret is missing. The dashboard where Chef schedules posts has its own login (see the `3c-control-center` repo).

## 7. Deploy

1. Open Cloudflare → Workers & Pages → `aurion-bot` → **Edit code**.
2. Replace all the code with `worker/worker.js` from this repo. **Deploy.**
3. Check that the bot answers (`/faq` or `/fact`) in Telegram.
4. Live check: opening `<worker address>/telegram` in a browser shows "Method not allowed" (405). That is correct.
5. Cron Triggers: Worker → Settings → Trigger Events → Cron Triggers. Add the 8 expressions from section 5, **one at a time**.
6. Dashboard → Settings → external services: a row `aurion-bot` with service type `aurion-bot` (the URL there is only a shortcut link). Schedule posts with that service type.
7. Webhook (once, or if the Worker address changes): Telegram `setWebhook` with the `/telegram` address, the same value as `TELEGRAM_WEBHOOK_SECRET`, and `allowed_updates` = `message`, `callback_query`. Only one thing can receive the bot's updates at a time.

## 8. Tests

Run on 22 Nov 2026 against a fake Telegram and fake Supabase (not in this repo): 83 checks for the bot and 112 for the scheduled run, all passed. They cover the four slots in winter and summer and both clock-change days, due-row selection with the real date formats, every formatting symbol, limits, media types, double-run protection, retries, the move to `dashboard_posts`, and failure messages.

The five checks of the Standard, for this Worker:

| Check | Result |
|---|---|
| Unsigned call refused | `POST /telegram` without the secret header answers 401 |
| Wrong account refused (403) | Not applicable: no owner routes |
| Owner call succeeds | Not applicable: no owner routes |
| Public read still works | Not applicable: no public routes |
| Wrong origin blocked | Not applicable: no browser calls |

Live: `/faq` answered after the 22 Nov deploy. First live test of the schedule: one text post on 22 Nov at the 08:30 slot, then one picture, one GIF and one video, each to a test chat before any real post.

## 9. Open points

- First live run of the schedule (22 Nov, 08:30) and the picture, GIF and video tests: results to be added here.
- `worker/wrangler.toml` still says observability enabled in the old copy; the new copy sets it to `false` (it is only a record).
- A scheduled row needs a real `user_id`; if it is missing, the post is sent but cannot be saved in `dashboard_posts`, and Chef is messaged. `post_platforms` has a link to `scheduled_posts` without cascade: if a row ever has entries there, the delete step fails and Chef is messaged.
- The old Python bot files (`main.py`, `Procfile`, `runtime.txt`, `requirements.txt`, `scheduled_posts_runner.py`) were removed on 22 Nov 2026. They stay in the Git history if ever needed.

## 10. Change log

| Date | Change | By |
|---|---|---|
| 22 Nov 2026 | Scheduled posting added to `worker/worker.js` (own timer, 8 Cron Triggers, lane `aurion-bot`); Render, the Vercel gateway and the old workflow removed; observability off for all Workers; README.md and SETUP.md written to the Standard; old Python bot files removed; database clean-up migrations of 21 Nov saved in `supabase/migrations/` | Champ |
| 20 Nov 2026 | Bot moved from Render to the Cloudflare Worker `aurion-bot`; `about_3c` table added | Champ |
