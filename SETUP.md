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
| **Cloudflare** | Worker `aurion-bot` and its one Cron Trigger. Workers Paid plan (the Worker needs the Paid plan for its CPU and request limits). Observability (stored logs) is **off and stays off**: Cloudflare switched it on for this Worker by itself on 22 Nov 2026 and Chef switched it off in the Worker's Settings, so check Settings, Observability after every deploy. |
| **Supabase**, project **3C Control Center** (`uqyqpwhkzlhqxcqajhkn`) | All the bot's tables, and `scheduled_posts` / `dashboard_posts` for the schedule. |
| **OpenAI** | Answers for `/ask` when the FAQ and keyword tables have nothing. |
| **GitHub** | This repository. No GitHub Actions are used by the bot. |

Removed on 22 Nov 2026 and no longer used: Render (bot and cron job), the Vercel cron gateway (`cron-gateway-auth`), Railway, and the old GitHub Actions posting workflow. The two old Supabase edge functions `telegram-bot` and `telegram-webhook-setup` (project 3C Control Center) were deleted on 23 Nov 2026; the Worker does all of their work.

## 4. Supabase (project 3C Control Center)

| Table | Used for | Row Level Security and access |
|---|---|---|
| `faq` | `/faq` buttons, first answer for `/ask` | On. Closed to everyone except the Worker's service key: its one SELECT policy compares `user_id` with the signed-in account, and every row has no `user_id`, so it matches nothing. |
| `fact` | `/fact` | On. Closed to everyone except the Worker's service key, same reason as `faq`. |
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
- **Cron Trigger (UTC), one only:** `0,30 * * * *` (every half hour). The slots are in the code, not in Cloudflare: **08:30, 10:30, 12:30, 14:30, 16:30, 18:30, 19:30, 20:30** Lisbon time. The squadron times are 08:30, 12:30, 18:30 and 20:30; the other four are free slots. Lisbon is UTC+0 in winter and UTC+1 in summer (whole hours), so :00 and :30 always line up. On each firing the Worker checks the real Lisbon clock and only runs if that half hour is a slot; otherwise it does nothing and logs nothing. A post goes out at the first slot at or after its scheduled time (a post set for 11:00 goes at 12:30). To change the slot times, edit `SCHED.slots` in `worker/worker.js` and paste again; the trigger stays the same.
- **Albums:** a post with 2 to 10 files in its media list is sent as one album, in the saved order, with the caption on the first item (caption limit 1,024 visible characters). Pictures and videos can be mixed. A GIF cannot be inside an album: that post fails with a clear reason and Chef is told. More than 10 files, files over 30 MB together, or a file that cannot be downloaded also fail without sending anything. A Telegram outage is retried like any other post. The saved post in `dashboard_posts` uses the first message number of the album.
- **Formatting:** text is sent as Telegram HTML. The Worker accepts `**bold**` (spaces inside are allowed, as the old Render runner did), `*italic*`, `__underline__`, `~~strike~~`, `` `code` ``, `[text](https://…)`, and Telegram's own `<b>`, `<i>`, `<u>`, `<s>`, `<code>` and `<a href="…">` tags. A link without `https://` that starts with `www.` gets `https://`. Text posts are sent with the link preview switched off, so no preview card (for example of a group invite) appears under the post. Any other `<`, `>` or `&` is made safe. If Telegram still refuses the formatting, the post is sent once as plain text and Chef is told.
- **What a run does:** takes up to 20 due rows of the lane `aurion-bot`; locks each row before sending (`status = 'processing'`); converts the dashboard symbols to Telegram formatting; sends text, a picture, a video or a GIF (no documents: use a thumbnail and a link); a post with two to ten pictures or videos goes out as one Telegram album; then marks the row sent, saves it in `dashboard_posts` and removes it from `scheduled_posts`.
- **Failures:** a content problem (text over 4,096 characters, caption over 1,024, file over 45 MB or missing, Telegram refusing, more than 24 hours late) is not retried: the row stays in `scheduled_posts` marked failed with the reason in `failure_reason`, and Chef gets a Telegram message. A network or Telegram outage is retried at the next slots, up to 3 tries in total, then the same message. A row left in `processing` after its 10-minute lock is never sent again blindly: Chef is told to check Telegram first.
- **Observability:** off. Failures reach Chef by Telegram message and are saved on the row.

## 6. Login

None. Members use Telegram; admin commands and failure messages are tied to the Telegram numeric ID in `BOT_ADMIN_TELEGRAM_ID`, and fail closed if that secret is missing. The dashboard where Chef schedules posts has its own login (see the `3c-control-center` repo).

## 7. Deploy

1. Open Cloudflare → Workers & Pages → `aurion-bot` → **Edit code**.
2. Replace all the code with `worker/worker.js` from this repo. **Deploy.**
3. Check that the bot answers (`/faq` or `/fact`) in Telegram.
4. Live check: opening `<worker address>/telegram` in a browser shows "Method not allowed" (405). That is correct.
5. Cron Trigger: Worker → Settings → Trigger Events → Cron Triggers. One expression only: `0,30 * * * *`. If old triggers are listed (the 8 from 22 Nov), add the new one first, then delete the old ones.
6. Dashboard → Settings → external services: a row `aurion-bot` with service type `aurion-bot` (the URL there is only a shortcut link). Schedule posts with that service type.
7. Webhook (once, or if the Worker address changes): Telegram `setWebhook` with the `/telegram` address, the same value as `TELEGRAM_WEBHOOK_SECRET`, and `allowed_updates` = `message`, `callback_query`. Only one thing can receive the bot's updates at a time.

## 8. Tests

Run on 22 Nov 2026 against a fake Telegram and fake Supabase (not in this repo): 83 checks for the bot and 112 for the scheduled run, all passed. Re-run on 22 Nov 2026 after the change to eight slots, the formatting fix and album sending (139 schedule checks). They cover every half hour of a winter day and a summer day (it sends at exactly the 8 slots), both clock-change days, every day of 2026, Chef's real post of 22 Nov, due-row selection with the real date formats, every formatting symbol, limits, media types, double-run protection, retries, the move to `dashboard_posts`, and failure messages.

The five checks of the Standard, for this Worker:

| Check | Result |
|---|---|
| Unsigned call refused | `POST /telegram` without the secret header answers 401 |
| Wrong account refused (403) | Not applicable: no owner routes |
| Owner call succeeds | Not applicable: no owner routes |
| Public read still works | Not applicable: no public routes |
| Wrong origin blocked | Not applicable: no browser calls |

Live: `/faq` answered after the 22 Nov deploy. First live test of the schedule: a text post at 11:00 on 22 Nov arrived on time and was saved in `dashboard_posts` as sent; its formatting did not come out (stars and link tags shown as text), which led to the formatting fix above. The 14:30 slot and the formatting were checked live and came out right. On 22 to 23 Nov 2026 Chef also tested an album of three pictures (saved as sent, one Telegram message id stored) and a single picture (saved as sent); both looked right in the chat. Still to test live: one GIF and one video, each to a test chat before any real post.

## 9. Open points

- Live tests still to do: one GIF and one video (test chat first); results to be added here. A post with pictures and no text stays refused (Chef's decision, 23 Nov 2026: a picture needs text).
- The dashboard still saves `**` and link tags for the Worker to convert. A separate dashboard job will make it save ready-made Telegram formatting; until then the Worker converts as described in section 5.
- Editing a sent post: in a Telegram group only the sender, here the bot, can edit a message, so a post in the ClubHouse chatroom cannot be edited by Chef; in a channel, admins can. Chef's way: post to the channel, check it, then forward to the chat. No Worker feature is planned for editing (Chef's decision, 22 Nov 2026).
- A scheduled row needs a real `user_id`; if it is missing, the post is sent but cannot be saved in `dashboard_posts`, and Chef is messaged. `post_platforms` has a link to `scheduled_posts` without cascade: if a row ever has entries there, the delete step fails and Chef is messaged.
- The old Python bot files (`main.py`, `Procfile`, `runtime.txt`, `requirements.txt`, `scheduled_posts_runner.py`) were removed on 22 Nov 2026. They stay in the Git history if ever needed.

## 10. Change log

| Date | Change | By |
|---|---|---|
| 23 Nov 2026 | Corrected the `faq` and `fact` rows in section 4 (they were wrongly marked public read; they are closed to everyone except the service key); recorded that the two old edge functions were deleted, the Observability note, and the live album and picture results; removed the outdated `wrangler.toml` open point | Champ |
| 22 Nov 2026 | Albums: two to ten pictures or videos in one post are sent as one Telegram album (caption on the first item; no GIFs inside an album) | Champ |
| 22 Nov 2026 | Eight posting slots (08:30, 10:30, 12:30, 14:30, 16:30, 18:30, 19:30, 20:30) on one half-hour Cron Trigger; formatting made as tolerant as the old Render runner (spaces inside `**`, hand-typed `<a href>` links and Telegram tags) | Champ |
| 22 Nov 2026 | Scheduled posting added to `worker/worker.js` (own timer, 8 Cron Triggers, lane `aurion-bot`); Render, the Vercel gateway and the old workflow removed; observability off for all Workers; README.md and SETUP.md written to the Standard; old Python bot files removed; database clean-up migrations of 21 Nov saved in `supabase/migrations/` | Champ |
| 20 Nov 2026 | Bot moved from Render to the Cloudflare Worker `aurion-bot`; `about_3c` table added | Champ |
