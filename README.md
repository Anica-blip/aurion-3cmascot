# 💎 Aurion Bot (aurion-3cmascot)

> ⚖️ This repository is protected under a binding [Legal Disclaimer](./LEGAL_DISCLAIMER.md) that governs all use, cloning, and forking from the date of inception. Please read before use.

> Aurion is the 3C community mascot and Telegram bot. He runs as a Cloudflare Worker called `aurion-bot`, answers members in the 3C Telegram community, and posts the scheduled 3C posts on his own timer.

---

**⚠️ Intellectual Property Notice**
This repository is open source under the MIT License — the code skeleton is free to clone and adapt.
The 3C Thread To Success™ brand, including its name, structure, characters (Caelum, Aurion, Jan, Casey, Anica), persona system (Falcon, Panther, Wolf, Lion), philosophy, and overall ecosystem identity remains the intellectual property of the creator and is **not** included in this license.
Commercial use of the brand or replication of the ecosystem identity is not permitted without permission.

---

## 🎭 The 3C Ecosystem

This project is part of a larger system built around five core identities:

**Aurion** → Engagement & Experience — 3C Mascot, community voice, diamond-energy guide
**Caelum** → Structure & Direction — Chief Advisor, PR Manager, Brand Integrity Officer
**Jan** → Clarity & Support — Writing & Editorial Support, Lifeline Mentor & Anchor
**Casey** → Story & Play — Creative Director, Lifeline Playmaker & Ace Maven
**Anica (Founder)** → Authority & Vision — Systems Strategist, Project Architect, the Chef

Together, they create a balanced environment for growth, learning, and progression.

---

## 💎 What Is Aurion Bot?

Aurion is the voice of the 3C Telegram community. Members talk to him with commands. He also posts the scheduled 3C posts that Chef sets up in the 3C Control Center dashboard.

What is inside:

- **Answers.** `/ask <question>` looks for an answer in this order: the FAQ table, then the keyword table, then OpenAI. If OpenAI is not available, Aurion sends a friendly "give me a moment" message and members never see the real error.
- **Welcome and goodbye.** New members get a welcome and leavers get a goodbye, in the same topic. `greeted_users` records who has been welcomed.
- **Scheduled posts.** Posts scheduled with the service type `aurion-bot` go out at the next of these Lisbon times: 08:30, 10:30, 12:30, 14:30, 16:30, 18:30, 19:30 and 20:30 (08:30, 12:30, 18:30 and 20:30 are the four squadron times). Text, pictures, videos and GIFs are supported, and two to ten pictures or videos in one post are sent together as an album. Text posts carry no link preview card. The Worker also understands the dashboard's `**bold**`, `*italic*`, `__underline__`, `~~strike~~`, `` `code` `` and `[link](https://...)` symbols and Telegram's own `<b>`, `<i>`, `<u>`, `<s>`, `<code>` and `<a href>` tags; the dashboard is being changed to save ready-made formatting. Documents (PDF) are not sent: use a thumbnail picture and a link.
- **Failure messages.** If a post cannot be sent (too long, a missing file, Telegram refusing it, more than 24 hours late), Aurion sends Chef a Telegram message with the post title, the slot and the reason. The post stays in `scheduled_posts`, marked failed, with the reason saved on it.

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

---

## ⚙️ How It Is Built

| Part | What it uses |
|---|---|
| Front end | None. Members use Telegram. Chef schedules posts in the 3C Control Center dashboard. |
| Database | Supabase, project **3C Control Center**: `faq`, `fact`, `keyword`, `greeted_users`, `about_3c`, and for scheduled posts `scheduled_posts` and `dashboard_posts` |
| Files (R2) | None |
| Workers | `aurion-bot` on Cloudflare: one private route (`POST /telegram`) and its own timer (one Cron Trigger, every half hour) |
| AI | OpenAI, only when no stored answer fits |
| Hosting | Cloudflare Workers |
| Admin access | The Telegram numeric ID kept in the Worker secret `BOT_ADMIN_TELEGRAM_ID` (admin command and failure messages). No web admin. |

The Worker is one file with no imports: `worker/worker.js`. Addresses, settings, secrets (names only) and the deploy steps are in [SETUP.md](SETUP.md).

---

## 🔐 Security and Privacy

- **Who can call the Worker.** Only Telegram, on `/telegram`, and only with the secret header. Anything else is refused. Any other address answers "not found". No browser calls the Worker, so it sends no CORS headers.
- **The timer is not a web address.** The scheduled run is started by Cloudflare itself. Nobody can trigger it from outside.
- **Who can read and write the data.** The Worker reads and writes Supabase with its service key, which lives only in the Worker's secrets. The `keyword` table is owner-only to read. `about_3c` and `greeted_users` are read through the service key only.
- **Admin.** `/dbstatus` and the failure messages go to one Telegram ID only. If that setting is missing, nobody can run the admin command.
- **Logs.** Cloudflare Observability (stored logs) is **off for the Worker and for all of Chef's Workers**, and stays off. Failures reach Chef by Telegram message and are saved as a reason on the row, so nothing depends on stored logs.
- **No secrets in the repository.** Secret values are never in code, files or chat. They are added only in the Cloudflare dashboard.

---

## 📖 Documentation

- [SETUP.md](SETUP.md) — every connection, setting, deploy step and test, in one place
- [LEGAL_DISCLAIMER.md](LEGAL_DISCLAIMER.md) — legal terms
- `supabase/migrations/` — the database changes for this bot, each with a rollback

---

## 🎨 Credits

*Designed and Built with ❤️ by Claude (Anthropic) × Chef Anica · 3C Thread To Success™ Cooking Lab* 🧪👨‍🍳

*"Think Smarter, Not Harder — Zero Shortcuts"*

---

## 👤 Creator

**Anica-blip ("Chef")**
Founder of 3C Thread To Success™ ("Cooking Lab")
Independent Creator | Community Builder

---

## 🧠 Philosophy

*"Think it. Do it. Own it."*

This project was built from vision, persistence, and a commitment to creating meaningful and structured experiences — even with minimal resources. Aurion exists so that every member of the community feels welcomed, answered and guided, at the right moment, without Chef having to be there for every one.
