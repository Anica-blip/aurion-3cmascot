# aurion-3cmascot

> ⚖️ This repository is protected under a binding [Legal Disclaimer](./LEGAL_DISCLAIMER.md) that governs all use, cloning, and forking from the date of inception. Please read before use.

This project is part of the 3C Thread To Success™ ecosystem — a growing digital platform that combines creativity, structure, and real-world application.

The 3C Thread To Success™ brand, including its name, structure, characters (Aurion 3C Mascot), and overall system design, remains the intellectual property of the creator and is not included in this license.

Commercial use of the brand or replication of the ecosystem identity is not permitted without permission.

---

Aurion is the 3C community mascot and Telegram bot. He runs as a **Cloudflare Worker** (`aurion-bot`) that receives Telegram updates through a webhook, answers from Supabase tables, and uses OpenAI when no stored answer fits.

## How it works

- Telegram sends each update to the Worker at `/telegram`. The Worker checks Telegram's secret header first and ignores anything that does not carry it.
- Only `message` and `callback_query` updates are accepted.
- `/ask <question>` looks for an answer in this order: **FAQ** table → **keyword** table → **OpenAI**. If OpenAI is unavailable, Aurion sends a friendly "give me a moment" message and the real error goes to the Worker logs only.
- New members get the welcome message and leavers get the goodbye, in the same topic. `greeted_users` records who has already been welcomed.

## Commands

| Command | What it does |
|---|---|
| `/start` | Welcome message |
| `/ask <question>` | FAQ, then keyword, then OpenAI |
| `/faq` | FAQ buttons |
| `/fact` | A random 3C fact |
| `/id` | The 3C links web app |
| `/rules` | Community rules |
| `/help` | Help text |
| `/hashtags` | Hashtag guide |
| `/topics` | Topic guide |
| `/dbstatus` | Admin only: database check |

The command menu members see in Telegram is set in BotFather (`/setcommands`), not in the code.

## Supabase

The bot reads from the **3C Control Center** project. It uses the service key from the Worker's secrets only.

| Table | Used for |
|---|---|
| `faq` | Question and answer buttons for `/faq`, and the first answer for `/ask` |
| `fact` | Random facts for `/fact` |
| `keyword` | Comma-separated triggers and their answers (whole-word match, longest trigger wins). Owner-only read. |
| `greeted_users` | Members already welcomed (`telegram_user_id`) |

## Deploying

The Worker is a single file with no imports: `worker/worker.js`. It is deployed by pasting that file into the Cloudflare dashboard (**Workers & Pages → aurion-bot → Edit code → Deploy**). No Wrangler CLI is needed. `worker/wrangler.toml` is a record of the settings only.

Add these as **Secrets** in the Worker (Settings → Variables and Secrets). Never put values in the repository or share them in chat:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET` (letters, digits, `_` and `-` only)
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `BOT_ADMIN_TELEGRAM_ID`

Register the webhook once with Telegram's `setWebhook`, pointing at the Worker's `/telegram` address, with the same secret as `TELEGRAM_WEBHOOK_SECRET` and `allowed_updates` set to `message` and `callback_query`. Opening `/telegram` in a browser shows "Method not allowed" — that is correct.

Only one thing can receive the bot's updates at a time: while the webhook is set, no other copy of the bot (for example a polling script) can run with the same token.

## Files in this repository

- `worker/` — the live bot (`worker.js`, `wrangler.toml`).
- `main.py`, `Procfile`, `runtime.txt`, `requirements.txt` — the earlier polling version of the bot. Retired and kept for reference only; it is no longer deployed.
- `scheduled_posts_runner.py` — not part of the bot. Kept for reference.
- `LEGAL_DISCLAIMER.md`, `LICENSE` — legal and licence terms.

## License

This project is licensed under the MIT License.

---

## 🎨 Credits

*Designed and Built with ❤ by Claude (Anthropic) × Chef Anica · 3C Thread To Success™ Cooking Lab 🧪👨🍳*

Think Smarter, Not Harder — Zero Shortcuts

---

## 👤 Creator

Anica-blip ("Chef")
Founder, 3C Thread To Success™
Independent Creator | Community Builder

---

## 🧠 Philosophy

"Think it. Do it. Own it."

This project was built from vision, persistence, and a commitment to creating meaningful and structured experiences, even with minimal resources.

Our vision: igniting a vibrant community where dreams ignite, and people are fired up to nurture a growth mindset that turns lives into purpose-driven adventures filled with passion!
