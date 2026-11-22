// Repo path: worker/worker.js
// ---------------------------------------------------------------------------
// Aurion bot — Cloudflare Worker (replaces main.py on Render)
// Like-for-like move: same commands, same wording, same Supabase tables.
//
// ROUTE TABLE
//   POST /telegram            -> PRIVATE. Telegram only. Needs the header
//                                X-Telegram-Bot-Api-Secret-Token = TELEGRAM_WEBHOOK_SECRET.
//   any other method on /telegram -> 405
//   everything else               -> 404
// No browser calls this Worker, so no CORS headers are sent.
// SCHEDULED RUN (no route; Cloudflare Cron Triggers call scheduled()): posts the rows in
//   scheduled_posts with service_type 'aurion-bot' at 08:30, 10:30, 12:30, 14:30, 16:30, 18:30,
//   19:30 and 20:30 Lisbon time, moves them to dashboard_posts, and messages BOT_ADMIN_TELEGRAM_ID
//   when something fails. ONE trigger: 0,30 * * * *  (every half hour; the Worker only acts at its
//   own slots, so changing a slot time is a code change only, never a Cloudflare trigger change).
// The one admin command (/dbstatus) is gated by the Telegram numeric id in
// BOT_ADMIN_TELEGRAM_ID and fails closed: if that secret is not set, nobody can run it.
//
// SECRETS (Cloudflare: Settings > Variables and Secrets, type "Secret"):
//   TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, OPENAI_API_KEY,
//   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, BOT_ADMIN_TELEGRAM_ID
//
// SUPABASE: 3C Control Center project, REST + service key only. Tables: faq, fact,
//   keyword, greeted_users (column telegram_user_id), about_3c (the briefing the AI
//   reads; written by Chief in the Drive sheet tab about_3c, service key only).
//   Scheduled run also reads and writes scheduled_posts and writes dashboard_posts.
//
// DEPLOY METHOD: Dashboard paste (Cloudflare > Workers & Pages > aurion-bot > Edit code).
//   One method only. Never mix with Wrangler. wrangler.toml is a record, not used to deploy.
// ---------------------------------------------------------------------------

// ===== Fixed texts: extracted from main.py by script, not retyped =====
const T = {
  "processing": [
    "Hey Champ, give me a second to help you with that!",
    "Hang tight, Champ! Aurion's on it.",
    "One moment, Champ—let me work my magic.",
    "Just a sec, Champ! Let me get that sorted for you."
  ],
  "signoff": "Keep crushing it, Champ! Aurion",
  "welcome": "Hey Champ, this is where our journey together begins! I'm here to guide you and help with anything community-related.\n\nJust remember to type /ask <u>followed by your question</u> whenever you want to talk to me. I don't listen in on conversations between members, so a little nudge is all it takes to get my attention.\n\nKeep crushing it, Champ! Aurion",
  "welcomeNewMember": "Hey Champ, nice to have you join the 3C community! 🎉\n\nTake your time to explore around and ask me anything. You'll find the cards here in this folder to know how to speak to me — it's going to be fun getting to speak to you too.\n\nKeep crushing it, Champ! Aurion",
  "goodbyeMember": "Hey Champ, we hope you enjoyed your time with us. Welcome back anytime.\n\nKeep crushing it, Champ! Aurion",
  "idText": "Check out our digital 3C /id card: https://anica-blip.github.io/3c-links/",
  "rulesText": "📜 Community Rules: https://t.me/c/2377255109/6/400",
  "helpText": "You can ask Aurion for tips, facts, or guidance. Try:\n/faq – Browse FAQs\n/fact – Get a random fact\n/rules – View community rules\n/id – Get the 3C Links web app\n",
  "topics": [
    [
      "Aurion Gems",
      "https://t.me/c/2377255109/138"
    ],
    [
      "ClubHouse Chatroom",
      "https://t.me/c/2377255109/10"
    ],
    [
      "ClubHouse News & Releases",
      "https://t.me/c/2377255109/6"
    ],
    [
      "ClubHouse Notices",
      "https://t.me/c/2377255109/674"
    ],
    [
      "Weekly Challenges",
      "https://t.me/c/2377255109/39"
    ],
    [
      "ClubHouse Mini-Challenges",
      "https://t.me/c/2377255109/25"
    ],
    [
      "ClubHouse Learning",
      "https://t.me/c/2377255109/12"
    ]
  ],
  "hashtags": [
    [
      "#Topics",
      "https://t.me/c/2431571054/58"
    ],
    [
      "#Blog",
      "https://t.me/c/2431571054/58"
    ],
    [
      "#Provisions",
      "https://t.me/c/2431571054/58"
    ],
    [
      "#Training",
      "https://t.me/c/2431571054/58"
    ],
    [
      "#Knowledge",
      "https://t.me/c/2431571054/58"
    ],
    [
      "#Language",
      "https://t.me/c/2431571054/58"
    ],
    [
      "#Audiobook",
      "https://t.me/c/2431571054/58"
    ],
    [
      "#Healingmusic",
      "https://t.me/c/2431571054/58"
    ]
  ],
  "askNoQuestion": "Champ, you gotta ask a question after /ask!",
  "fetchFail": "Sorry, Champ! Aurion can't fetch this right now due to technical issues.",
  "selectFaq": "Select a FAQ:",
  "noAnswer": "No answer found.",
  "factPrefix": "💎 Aurion Fact:\n",
  "dbNotConfigured": "Database not configured. Admins: check SUPABASE env vars.",
  "adminOnly": "This command is only available to the Aurion team, Champ.",
  "dbClientNotConfigured": "DB client not configured (USE_MODE is None).",
  "dbStatusPrefix": "DB status:\n",
  "truncated": "\n\n...[truncated]",
  "openaiSystemPrompt": "You are Aurion, the 3C Mascot: energetic, motivating, a bit cheeky, and always supportive. Reply in 1-2 short paragraphs. Vary your phrasing for returning users. After your answer, always add this signoff, no line break, just space after the last full stop: 'Keep crushing it, Champ! Aurion'",
  "askFailure": "Champ, give me a moment, we're having some tech issues right now. Aurion is on it, so please try again in a little while.",
  "aboutRules": "Rules for answering (set by the 3C team):\n- Use only the 3C information below and the member's question. Do not add facts about 3C from anywhere else.\n- If the answer is not covered below, say so warmly and point the member to the 3C Public Library, or to Drop In in the Pop In folder to reach the team. Share a link only if it appears below.\n- Never invent facts, links, dates, prices or promises about future content.\n- Never give health, money or legal advice; kindly suggest a qualified professional.",
  "aboutHeading": "3C information (written by the 3C team):",
  "aboutMissing": "The 3C information could not be loaded right now. Do not state facts about 3C. Warmly point the member to the 3C Public Library instead."
};

// ===== End of fixed texts =====

const SEEN_LIMIT = 200;
const seenIds = [];
const seenSet = new Set();
let botUsernameCache = null;

// ---------- small helpers ----------

function safeEqual(a, b) {
  const enc = new TextEncoder();
  const x = enc.encode(String(a));
  const y = enc.encode(String(b));
  let diff = x.length ^ y.length;
  const n = Math.max(x.length, y.length);
  for (let i = 0; i < n; i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Same behaviour as ensure_signoff_once in main.py
function ensureSignoffOnce(answer, signoff) {
  const re = new RegExp("[\\s.]*" + escapeRegExp(signoff) + "[\\s.]*$");
  let a = String(answer).trim().replace(re, "");
  if (!/[.!?]$/.test(a)) a += ".";
  return a + " " + signoff;
}

function seenBefore(updateId) {
  if (typeof updateId !== "number") return false;
  if (seenSet.has(updateId)) return true;
  seenSet.add(updateId);
  seenIds.push(updateId);
  if (seenIds.length > SEEN_LIMIT) seenSet.delete(seenIds.shift());
  return false;
}

function dbConfigured(env) {
  return Boolean(env.SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY);
}

// ---------- Telegram ----------

async function tg(env, method, payload) {
  const res = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    data = null;
  }
  if (!res.ok || !data || !data.ok) {
    // never include the URL here: it contains the bot token
    throw new Error(`Telegram ${method} failed: ${(data && data.description) || res.status}`);
  }
  return data;
}

// Replies land in the same forum topic, but only when the message really is a topic message.
function reply(env, msg, text, extra) {
  const payload = { chat_id: msg.chat.id, text, ...(extra || {}) };
  if (msg.is_topic_message && msg.message_thread_id !== undefined) {
    payload.message_thread_id = msg.message_thread_id;
  }
  return tg(env, "sendMessage", payload);
}

async function getBotUsername(env) {
  if (botUsernameCache) return botUsernameCache;
  try {
    const r = await tg(env, "getMe", {});
    botUsernameCache = (r.result && r.result.username) || null;
  } catch (e) {
    console.error("getMe failed:", e && e.message);
  }
  return botUsernameCache;
}

// Accepts /cmd and /cmd@ThisBot; ignores /cmd@SomeOtherBot. The command must be at
// the very start of the message (a bot_command entity at offset 0).
async function parseCommand(env, msg) {
  const text = msg.text;
  if (typeof text !== "string" || !text.startsWith("/")) return null;
  const ent = (msg.entities || []).find((e) => e.type === "bot_command" && e.offset === 0);
  if (!ent) return null;
  const token = text.slice(1, ent.length);
  const parts = token.split("@");
  const command = parts[0].toLowerCase();
  if (parts.length > 1) {
    const username = await getBotUsername(env);
    if (!username || parts[1].toLowerCase() !== username.toLowerCase()) return null;
  }
  const args = text.trim().split(/\s+/).slice(1);
  return { command, args };
}

// ---------- Supabase (REST, service key) ----------

async function sb(env, path, opts) {
  const o = opts || {};
  const key = env.SUPABASE_SERVICE_ROLE_KEY;
  const headers = { apikey: key, Accept: "application/json", ...(o.headers || {}) };
  if (key.startsWith("eyJ")) headers.Authorization = `Bearer ${key}`; // legacy JWT-style keys
  const res = await fetch(`${env.SUPABASE_URL.replace(/\/+$/, "")}/rest/v1/${path}`, {
    method: o.method || "GET",
    headers,
    body: o.body,
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`Supabase ${res.status}: ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

async function hasGreeted(env, userId) {
  try {
    const rows = await sb(env, `greeted_users?select=telegram_user_id&telegram_user_id=eq.${encodeURIComponent(userId)}&limit=1`);
    return Boolean(rows && rows.length);
  } catch (e) {
    console.error("hasGreeted error:", e && e.message);
    return false; // same as main.py: on error, treat as not greeted
  }
}

async function markGreeted(env, userId) {
  try {
    await sb(env, "greeted_users?on_conflict=telegram_user_id", {
      method: "POST",
      headers: { "Content-Type": "application/json", Prefer: "resolution=ignore-duplicates,return=minimal" },
      body: JSON.stringify({ telegram_user_id: userId }),
    });
  } catch (e) {
    console.error("markGreeted error:", e && e.message);
  }
}

// FAQ search: the member's text is never put into the database address. The faq
// table is tiny, so it is read in full and matched here (contains, ignoring case,
// first row by id). This cannot be tricked by %, _, *, commas or brackets.
async function getFaqAnswer(env, question) {
  try {
    const rows = await sb(env, "faq?select=id,question,answer&order=id.asc");
    const needle = question.toLowerCase();
    const hit = (rows || []).find((r) => typeof r.question === "string" && r.question.toLowerCase().includes(needle));
    return hit ? hit.answer : null;
  } catch (e) {
    console.error("getFaqAnswer error:", e && e.message);
    return null;
  }
}

// Keyword table: each row may hold several comma-separated triggers. A trigger matches
// as a whole word, ignoring case. The longest matching trigger wins.
async function getKeywordAnswer(env, question) {
  let rows;
  try {
    rows = await sb(env, "keyword?select=keyword,answer");
  } catch (e) {
    console.error("getKeywordAnswer error:", e && e.message);
    return null;
  }
  let bestAnswer = null;
  let bestLen = 0;
  for (const row of rows || []) {
    if (!row.keyword || !row.answer) continue;
    for (let trigger of row.keyword.split(",")) {
      trigger = trigger.trim();
      if (!trigger) continue;
      const re = new RegExp("(?<![\\p{L}\\p{N}_])" + escapeRegExp(trigger) + "(?![\\p{L}\\p{N}_])", "iu");
      if (re.test(question) && trigger.length > bestLen) {
        bestLen = trigger.length;
        bestAnswer = row.answer;
      }
    }
  }
  return bestAnswer;
}

async function fetchFaqList(env) {
  try {
    return (await sb(env, "faq?select=id,question&order=id.asc")) || [];
  } catch (e) {
    console.error("fetchFaqList error:", e && e.message);
    return [];
  }
}

async function fetchFaqAnswerById(env, id) {
  if (!/^\d+$/.test(id)) return null;
  try {
    const rows = await sb(env, `faq?select=answer&id=eq.${id}&limit=1`);
    return rows && rows.length ? rows[0].answer : null;
  } catch (e) {
    console.error("fetchFaqAnswerById error:", e && e.message);
    return null;
  }
}

async function fetchFacts(env) {
  try {
    const rows = (await sb(env, "fact?select=fact")) || [];
    return rows.map((r) => r.fact);
  } catch (e) {
    console.error("fetchFacts error:", e && e.message);
    return [];
  }
}

// ---------- OpenAI ----------

// The briefing the AI reads with every question (table about_3c, id order). If it cannot
// be read, the AI is told so and must not state facts about 3C.
async function fetchAbout(env) {
  try {
    const rows = (await sb(env, "about_3c?select=id,topic,info,link&order=id.asc")) || [];
    return rows
      .filter((r) => r && r.info && String(r.info).trim())
      .map((r) => `- ${String(r.topic || "").trim()}: ${String(r.info).trim()}${r.link ? ` (Link: ${String(r.link).trim()})` : ""}`)
      .join("\n");
  } catch (e) {
    console.error("fetchAbout error:", e && e.message);
    return "";
  }
}

async function buildSystemPrompt(env) {
  const about = await fetchAbout(env);
  const briefing = about ? `${T.aboutHeading}\n${about}` : T.aboutMissing;
  return `${T.openaiSystemPrompt}\n\n${T.aboutRules}\n\n${briefing}`;
}

async function askOpenAI(env, question) {
  if (!env.OPENAI_API_KEY) throw new Error("OpenAI client not configured (OPENAI_API_KEY missing).");
  const systemPrompt = await buildSystemPrompt(env);
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${env.OPENAI_API_KEY}` },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: question },
      ],
      max_tokens: 300,
    }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok || !data || !data.choices || !data.choices[0]) {
    throw new Error(`OpenAI ${res.status}: ${data && data.error ? data.error.message : "no answer"}`);
  }
  return String(data.choices[0].message.content).trim();
}

// ---------- Command handlers ----------

async function cmdStart(env, msg) {
  if (!msg.from) return;
  const userId = msg.from.id;
  const greeted = await hasGreeted(env, userId);
  if (!greeted) {
    await reply(env, msg, T.welcome, { parse_mode: "HTML" });
    await markGreeted(env, userId);
  } else {
    await reply(env, msg, pick(T.processing));
  }
}

async function cmdAsk(env, msg, args) {
  if (!args.length) {
    await reply(env, msg, T.askNoQuestion);
    return;
  }
  const question = args.join(" ");
  await reply(env, msg, pick(T.processing));
  try {
    let answer;
    const faqAnswer = await getFaqAnswer(env, question);
    if (faqAnswer) {
      answer = ensureSignoffOnce(faqAnswer, T.signoff);
    } else {
      const keywordAnswer = await getKeywordAnswer(env, question);
      if (keywordAnswer) {
        answer = ensureSignoffOnce(keywordAnswer, T.signoff);
      } else {
        answer = ensureSignoffOnce(await askOpenAI(env, question), T.signoff);
      }
    }
    await reply(env, msg, answer);
  } catch (e) {
    console.error("Ask handler error:", e && e.message);
    await reply(env, msg, ensureSignoffOnce(T.askFailure, T.signoff));
  }
}

async function cmdFaq(env, msg) {
  if (!dbConfigured(env)) {
    await reply(env, msg, T.dbNotConfigured);
    return;
  }
  const faqs = await fetchFaqList(env);
  if (!faqs.length) {
    await reply(env, msg, T.fetchFail);
    return;
  }
  const inline_keyboard = faqs.map((q) => [{ text: q.question, callback_data: `faq_${q.id}` }]);
  await reply(env, msg, T.selectFaq, { reply_markup: { inline_keyboard } });
}

async function cmdFact(env, msg) {
  if (!dbConfigured(env)) {
    await reply(env, msg, T.dbNotConfigured);
    return;
  }
  const facts = await fetchFacts(env);
  if (facts.length) {
    await reply(env, msg, `${T.factPrefix}${pick(facts)}`);
  } else {
    await reply(env, msg, T.fetchFail);
  }
}

async function cmdTopics(env, msg) {
  const lines = T.topics.map(([t, u], i) => `${i + 1}) [${t}](${u})`);
  await reply(env, msg, lines.join("\n"), { parse_mode: "Markdown" });
}

async function cmdHashtags(env, msg) {
  const lines = T.hashtags.map(([t, u]) => `[${t}](${u})`);
  await reply(env, msg, lines.join("\n"), { parse_mode: "Markdown" });
}

function isAdmin(env, msg) {
  const admin = String(env.BOT_ADMIN_TELEGRAM_ID || "").trim();
  if (!admin || !msg.from) return false;
  return String(msg.from.id) === admin;
}

async function cmdDbStatus(env, msg) {
  if (!isAdmin(env, msg)) {
    await reply(env, msg, T.adminOnly);
    return;
  }
  if (!dbConfigured(env)) {
    await reply(env, msg, T.dbClientNotConfigured);
    return;
  }
  const out = { mode: "rest_service" };
  try {
    out.faq_sample = { data: await sb(env, "faq?select=id,question&limit=1"), error: null };
    out.fact_sample = { data: await sb(env, "fact?select=id,fact&limit=1"), error: null };
  } catch (e) {
    out.exception = String((e && e.message) || e);
  }
  let text = JSON.stringify(out, null, 2);
  if (text.length > 3800) text = text.slice(0, 3800) + T.truncated;
  await reply(env, msg, T.dbStatusPrefix + text);
}

const COMMANDS = {
  start: (env, msg) => cmdStart(env, msg),
  ask: (env, msg, args) => cmdAsk(env, msg, args),
  faq: (env, msg) => cmdFaq(env, msg),
  fact: (env, msg) => cmdFact(env, msg),
  id: (env, msg) => reply(env, msg, T.idText),
  rules: (env, msg) => reply(env, msg, T.rulesText),
  help: (env, msg) => reply(env, msg, T.helpText),
  hashtags: (env, msg) => cmdHashtags(env, msg),
  topics: (env, msg) => cmdTopics(env, msg),
  dbstatus: (env, msg) => cmdDbStatus(env, msg),
};

// ---------- Events ----------

async function welcomeNewMembers(env, msg) {
  for (const member of msg.new_chat_members || []) {
    if (member.is_bot) continue;
    const payload = { chat_id: msg.chat.id, text: T.welcomeNewMember };
    if (msg.message_thread_id !== undefined) payload.message_thread_id = msg.message_thread_id;
    await tg(env, "sendMessage", payload);
  }
}

async function farewellMember(env, msg) {
  if (msg.left_chat_member.is_bot) return;
  const payload = { chat_id: msg.chat.id, text: T.goodbyeMember };
  if (msg.message_thread_id !== undefined) payload.message_thread_id = msg.message_thread_id;
  await tg(env, "sendMessage", payload);
}

async function handleCallback(env, cq) {
  const data = cq.data || "";
  // Always acknowledge, or the member's button keeps spinning.
  await tg(env, "answerCallbackQuery", { callback_query_id: cq.id });
  if (!data.startsWith("faq_") || !cq.message) return;
  let text;
  if (!dbConfigured(env)) {
    text = T.dbNotConfigured;
  } else {
    text = (await fetchFaqAnswerById(env, data.replace("faq_", ""))) || T.noAnswer;
  }
  await tg(env, "editMessageText", { chat_id: cq.message.chat.id, message_id: cq.message.message_id, text });
}

async function handleMessage(env, msg) {
  if (!msg.chat) return;
  if (msg.new_chat_members && msg.new_chat_members.length) return welcomeNewMembers(env, msg);
  if (msg.left_chat_member) return farewellMember(env, msg);
  const parsed = await parseCommand(env, msg);
  if (!parsed) return; // ordinary conversation is ignored
  const handler = COMMANDS[parsed.command];
  if (!handler) return; // unknown commands are ignored
  return handler(env, msg, parsed.args);
}

async function handleUpdate(env, update) {
  try {
    if (seenBefore(update.update_id)) {
      console.log("Duplicate update skipped:", update.update_id);
      return;
    }
    if (update.callback_query) await handleCallback(env, update.callback_query);
    else if (update.message) await handleMessage(env, update.message);
    // edited messages, channel posts and everything else are ignored
  } catch (e) {
    console.error("Exception while handling an update:", (e && e.stack) || e);
  }
}

// ---------- Scheduled posting (Cloudflare Cron Triggers) ----------
// The Worker's own timer. Lane = scheduled_posts.service_type 'aurion-bot'.
// Slots (Lisbon time): 08:30, 10:30, 12:30, 14:30, 16:30, 18:30, 19:30, 20:30.
// The squadron times are 08:30, 12:30, 18:30 and 20:30; the other four are free slots.
// ONE Cron Trigger every half hour (0,30 * * * *, UTC). Lisbon is UTC+0 in winter and UTC+1 in
// summer, whole hours, so :00 and :30 always line up. The run checks the real Lisbon clock and
// does nothing (no log) unless that half hour is a slot. A post goes out at the first slot at or
// after its scheduled time. See SETUP.md.

const SCHED = {
  lane: "aurion-bot",
  zone: "Europe/Lisbon",
  slots: ["08:30", "10:30", "12:30", "14:30", "16:30", "18:30", "19:30", "20:30"],
  maxPerRun: 20, // rows sent in one run; the rest wait for the next slot
  lockMinutes: 10,
  maxTries: 3, // first try + 2 more, only for outages
  overdueMs: 24 * 60 * 60 * 1000,
  mediaMaxBytes: 45 * 1024 * 1024,
  textMax: 4096,
  captionMax: 1024,
};

const JSON_HEADERS = { "Content-Type": "application/json" };

// Lisbon wall-clock date and time for an instant (same method as the Render runner: Intl).
function lisbonParts(ms) {
  const parts = {};
  const fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone: SCHED.zone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  for (const p of fmt.formatToParts(new Date(ms))) if (p.type !== "literal") parts[p.type] = p.value;
  const hour = parts.hour === "24" ? "00" : parts.hour;
  return { date: `${parts.year}-${parts.month}-${parts.day}`, time: `${hour}:${parts.minute}:${parts.second}`, hm: `${hour}:${parts.minute}` };
}

// Wall-clock "YYYY-MM-DD" + "HH:MM[:SS]" as a comparable number (NaN when unreadable).
function wallStamp(dateStr, timeStr) {
  const d = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dateStr || ""));
  const t = /^(\d{2}):(\d{2})(?::(\d{2}))?/.exec(String(timeStr || ""));
  if (!d || !t) return NaN;
  return Date.UTC(+d[1], +d[2] - 1, +d[3], +t[1], +t[2], +(t[3] || 0));
}

// ----- Text -> Telegram HTML -----

function escHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const MARK_TAG = { "**": "b", "__": "u", "~~": "s", "*": "i", "_": "i" };

// Input is already HTML-escaped. Turns **bold**, __underline__, ~~strike~~, *italic*, _italic_
// into tags that are always properly nested; a marker with no partner stays as plain text.
function inlineFormat(s) {
  const isWord = (c) => c !== undefined && /[\p{L}\p{N}_]/u.test(c);
  const items = [];
  let buf = "";
  let i = 0;
  while (i < s.length) {
    const two = s.substr(i, 2);
    const c = s[i];
    let m = null;
    if (two === "**" || two === "__" || two === "~~") m = two;
    else if (c === "*" || c === "_") m = c;
    if (!m) {
      buf += c;
      i++;
      continue;
    }
    const prev = i > 0 ? s[i - 1] : undefined;
    const next = s[i + m.length];
    let canOpen = next !== undefined && !/\s/.test(next);
    let canClose = prev !== undefined && !/\s/.test(prev);
    if (m === "_") {
      canOpen = canOpen && !isWord(prev);
      canClose = canClose && !isWord(next);
    }
    // Same as the old Render runner: ** __ ~~ may have spaces inside ("** text **"). A single
    // * or _ stays strict so "2 * 3 * 4" is not turned into italics.
    if (m.length === 2) {
      canOpen = next !== undefined;
      canClose = prev !== undefined;
    }
    if (buf) items.push({ text: buf });
    buf = "";
    items.push({ mark: m, canOpen, canClose, pair: null, role: null });
    i += m.length;
  }
  if (buf) items.push({ text: buf });

  const stack = [];
  let pairId = 0;
  for (let k = 0; k < items.length; k++) {
    const it = items[k];
    if (!it.mark) continue;
    let j = -1;
    if (it.canClose) {
      for (let x = stack.length - 1; x >= 0; x--) {
        if (items[stack[x]].mark === it.mark) {
          j = x;
          break;
        }
      }
    }
    if (j >= 0) {
      const o = items[stack[j]];
      stack.splice(j, 1);
      pairId++;
      o.pair = it.pair = pairId;
      o.role = "open";
      it.role = "close";
    } else if (it.canOpen) {
      stack.push(k);
    }
  }

  let out = "";
  let open = []; // currently open tags: { pair, tag }
  for (const it of items) {
    if (it.text !== undefined) {
      out += it.text;
    } else if (it.role === "open") {
      out += `<${MARK_TAG[it.mark]}>`;
      open.push({ pair: it.pair, tag: MARK_TAG[it.mark] });
    } else if (it.role === "close") {
      const p = open.findIndex((e) => e.pair === it.pair);
      const popped = open.splice(p);
      for (let x = popped.length - 1; x >= 0; x--) out += `</${popped[x].tag}>`;
      for (let x = 1; x < popped.length; x++) {
        out += `<${popped[x].tag}>`;
        open.push(popped[x]);
      }
    } else {
      out += it.mark; // marker with no partner: literal text
    }
  }
  for (let x = open.length - 1; x >= 0; x--) out += `</${open[x].tag}>`; // safety: never leave a tag open
  // spaces just inside a tag move outside it: "<b> text </b>" -> " <b>text</b> "
  out = out.replace(/<(b|i|u|s)>([ \t]+)/g, "$2<$1>").replace(/([ \t]+)<\/(b|i|u|s)>/g, "</$2>$1");
  let prevOut;
  do {
    prevOut = out;
    out = out.replace(/<(b|i|u|s)><\/\1>/g, "");
  } while (out !== prevOut);
  return out;
}

// Telegram only accepts a few HTML tags. Dashboard text may already contain them (the old Render
// runner passed them through), so these are kept; any other < > & is made safe.
const RAW_TAGS = { b: "b", strong: "b", i: "i", em: "i", u: "u", ins: "u", s: "s", strike: "s", del: "s", code: "code" };
const RAW_ANCHOR = /<a\s[^>]*?href\s*=\s*(?:"([^"]*)"|'([^']*)')[^>]*>([\s\S]*?)<\/a\s*>/gi;

// href for Telegram: needs a full address. "www.x.y" gets https://. Anything else unsafe -> null.
function safeHref(u) {
  let url = String(u).trim().replace(/&amp;/gi, "&");
  if (/^www\./i.test(url)) url = "https://" + url;
  if (!/^(https?:\/\/|tg:\/\/|mailto:)/i.test(url)) return null;
  return escHtml(url).replace(/"/g, "&quot;");
}

// Dashboard text (with ** * _ __ ~~ ` [text](url) and Telegram HTML tags) -> Telegram HTML.
function mdToHtml(raw) {
  let s = String(raw).replace(/\u0000/g, "");
  const keep = [];
  const hold = (html) => {
    keep.push(html);
    return `\u0000${keep.length - 1}\u0000`;
  };
  // 1. HTML links written by hand: <a href="..." target=... rel=...>text</a> -> <a href="...">text</a>
  s = s.replace(RAW_ANCHOR, (_m, d, sq, text) => {
    const href = safeHref(d !== undefined ? d : sq);
    const label = inlineFormat(escHtml(text));
    return hold(href ? `<a href="${href}">${label}</a>` : label);
  });
  // 2. Plain Telegram tags, only when every opening tag has its closing tag
  for (const name of Object.keys(RAW_TAGS)) {
    const openRe = new RegExp(`<${name}>`, "gi");
    const closeRe = new RegExp(`</${name}>`, "gi");
    const o = (s.match(openRe) || []).length;
    const c = (s.match(closeRe) || []).length;
    if (o === 0 || o !== c) continue;
    s = s.replace(openRe, () => hold(`<${RAW_TAGS[name]}>`)).replace(closeRe, () => hold(`</${RAW_TAGS[name]}>`));
  }
  // 3. everything else: < > & made safe
  s = escHtml(s);
  s = s.replace(/`([^`\n]+)`/g, (_m, c) => hold(`<code>${c}</code>`));
  s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, label, url) =>
    hold(`<a href="${url.replace(/"/g, "%22")}">${inlineFormat(label)}</a>`)
  );
  s = inlineFormat(s);
  for (let n = 0; n < 3 && s.includes("\u0000"); n++) {
    s = s.replace(/\u0000(\d+)\u0000/g, (_m, idx) => keep[+idx]);
  }
  return s;
}

// Same text with no formatting at all (used only if Telegram refuses the formatted version).
function mdToPlain(raw) {
  return String(raw)
    .replace(/\u0000/g, "")
    .replace(RAW_ANCHOR, (_m, d, sq, text) => `${text} (${d !== undefined ? d : sq})`)
    .replace(/<\/?(b|strong|i|em|u|ins|s|strike|del|code)>/gi, "")
    .replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, "$1 ($2)")
    .replace(/\*\*|__|~~|`/g, "");
}

function visibleLength(html) {
  return html.replace(/<[^>]*>/g, "").replace(/&(amp|lt|gt);/g, "x").length;
}

function contentOf(row) {
  const pc = row.post_content;
  return pc && typeof pc === "object" && !Array.isArray(pc) ? pc : null;
}

// Same layout as the Render runner (name block, title, description, hashtags, cta),
// but the converter runs on every row.
function buildPostText(row, mode) {
  const html = mode === "html";
  const esc = html ? escHtml : (x) => String(x);
  const fmt = html ? mdToHtml : mdToPlain;
  const tagLine = (list) => list.map((t) => String(t)).map((t) => (t.startsWith("#") ? t : `#${t}`)).join(" ");
  const pc = contentOf(row);
  let out = "";
  if (!pc) {
    if (row.title) out += `${fmt(row.title)}\n\n`;
    if (row.description) out += `${fmt(row.description)}\n`;
    if (Array.isArray(row.hashtags) && row.hashtags.length) out += `\n${esc(tagLine(row.hashtags))}`;
    if (row.cta) out += `\n\n👉 ${fmt(row.cta)}`;
    return out.trim();
  }
  const name = pc.name || row.name;
  const username = pc.username || row.username;
  const role = pc.role || row.role;
  if (name) {
    out += html ? `<b>${esc(name)}</b>\n` : `${name}\n`;
    if (username) {
      const u = String(username);
      out += `${esc(u.startsWith("@") ? u : `@${u}`)}\n`;
    }
    if (role) out += `${esc(role)}\n`;
    out += "\n";
  }
  if (pc.title) out += `${fmt(pc.title)}\n\n`;
  if (pc.description) out += `${fmt(pc.description)}\n`;
  if (Array.isArray(pc.hashtags) && pc.hashtags.length) out += `\n${esc(tagLine(pc.hashtags))}`;
  if (pc.cta) out += `\n\n👉 ${fmt(pc.cta)}`;
  return out.trim();
}

// ----- Media -----

// First media file: from the row's media_files, else from inside post_content.
function pickMedia(row) {
  let list = Array.isArray(row.media_files) && row.media_files.length ? row.media_files : null;
  if (!list) {
    const pc = contentOf(row);
    if (pc && Array.isArray(pc.media_files) && pc.media_files.length) list = pc.media_files;
  }
  if (!list) return null;
  const first = list[0];
  const url = first && typeof first === "object" ? first.url || first.src || first.supabaseUrl : first;
  if (typeof url !== "string" || !/^https?:\/\//i.test(url)) return { error: "The media file has no usable web address." };
  const type = String((first && first.type) || "").toLowerCase();
  const name = String((first && first.name) || "").toLowerCase();
  const path = url.split(/[?#]/)[0].toLowerCase();
  let kind = "photo";
  if (type === "animation" || type === "gif" || path.endsWith(".gif") || name.endsWith(".gif")) kind = "animation";
  else if (type === "video" || /\.(mp4|mov|avi|mkv|webm)$/.test(path)) kind = "video";
  return { url, kind };
}

const MEDIA_SEND = {
  photo: { method: "sendPhoto", field: "photo", mime: "image/jpeg", def: "photo.jpg" },
  video: { method: "sendVideo", field: "video", mime: "video/mp4", def: "video.mp4" },
  animation: { method: "sendAnimation", field: "animation", mime: "image/gif", def: "animation.gif" },
};

async function fetchMedia(url) {
  let res;
  try {
    res = await fetch(url);
  } catch (e) {
    return { error: "Could not reach the media file address.", outage: true };
  }
  if (!res.ok) {
    return { error: `Could not download the media file (HTTP ${res.status}).`, outage: res.status >= 500 || res.status === 429 };
  }
  const tooBig = (n) => ({ error: `The media file is ${(n / 1048576).toFixed(1)} MB; the limit is 45 MB.`, outage: false });
  const len = Number(res.headers.get("content-length"));
  if (len > SCHED.mediaMaxBytes) return tooBig(len);
  let bytes;
  try {
    bytes = await res.arrayBuffer();
  } catch (e) {
    return { error: "The download of the media file was interrupted.", outage: true };
  }
  if (bytes.byteLength > SCHED.mediaMaxBytes) return tooBig(bytes.byteLength);
  let name = url.split(/[?#]/)[0].split("/").pop() || "";
  try {
    name = decodeURIComponent(name);
  } catch (e) {
    /* keep as is */
  }
  return { bytes, name };
}

// ----- Telegram sending (reports the outcome instead of throwing) -----

async function schedTg(env, method, payload, file) {
  const url = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`;
  let res;
  try {
    if (file) {
      const form = new FormData();
      for (const [k, v] of Object.entries(payload)) if (v !== undefined && v !== null) form.append(k, String(v));
      form.append(file.field, new Blob([file.bytes], { type: file.mime }), file.name);
      res = await fetch(url, { method: "POST", body: form });
    } else {
      res = await fetch(url, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(payload) });
    }
  } catch (e) {
    // never include the URL: it contains the bot token
    return { ok: false, status: 0, description: "Network error while talking to Telegram" };
  }
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    data = null;
  }
  if (res.ok && data && data.ok) {
    const id = data.result && data.result.message_id;
    return { ok: true, status: res.status, messageId: id !== undefined && id !== null ? String(id) : null };
  }
  return { ok: false, status: res.status, description: (data && data.description) || `HTTP ${res.status}` };
}

function isOutage(r) {
  return r.status === 0 || r.status === 429 || r.status >= 500;
}

// Formatted first; if Telegram refuses the formatting, the same post goes once more as plain text.
async function deliverRow(env, row, chatId, thread, media, file) {
  const attempt = (mode) => {
    const text = buildPostText(row, mode);
    const payload = { chat_id: chatId };
    if (thread) payload.message_thread_id = thread;
    if (mode === "html") payload.parse_mode = "HTML";
    if (file) {
      if (text) payload.caption = text;
      return schedTg(env, MEDIA_SEND[media.kind].method, payload, file);
    }
    payload.text = text;
    payload.link_preview_options = { is_disabled: true }; // no preview card under the post (Chef, 22 Nov)
    return schedTg(env, "sendMessage", payload);
  };
  const first = await attempt("html");
  if (!first.ok && first.status === 400 && /can't parse entities|can't find end/i.test(first.description || "")) {
    const second = await attempt("plain");
    if (second.ok) second.plain = true;
    return second;
  }
  return first;
}

// ----- Supabase rows -----

function rowTitle(row) {
  const pc = contentOf(row);
  const t = String(row.title || (pc && pc.title) || row.id || "(no title)");
  return mdToPlain(t).replace(/\s+/g, " ").slice(0, 80);
}

async function alertChef(env, text) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.BOT_ADMIN_TELEGRAM_ID) {
    console.error("Could not alert Chef: bot token or BOT_ADMIN_TELEGRAM_ID is missing");
    return;
  }
  try {
    await tg(env, "sendMessage", { chat_id: env.BOT_ADMIN_TELEGRAM_ID, text: String(text).slice(0, 3800) });
  } catch (e) {
    console.error("Could not alert Chef:", e && e.message);
  }
}

// One conditional update on one row; returns the rows that changed.
async function patchRow(env, row, extraFilter, body) {
  const q = `scheduled_posts?id=eq.${encodeURIComponent(row.id)}&service_type=eq.${SCHED.lane}${extraFilter || ""}`;
  return sb(env, q, { method: "PATCH", headers: { ...JSON_HEADERS, Prefer: "return=representation" }, body: JSON.stringify(body) });
}

// Content problem: no retry. Row stays in scheduled_posts, marked failed, with the reason; Chef is told.
async function failRow(env, row, slot, reason, whatNow) {
  let note = "";
  try {
    const hit = await patchRow(env, row, "&posting_status=eq.pending", {
      posting_status: "failed",
      status: "failed",
      failure_reason: String(reason).slice(0, 500),
      runner_locked_until: null,
      updated_at: new Date().toISOString(),
    });
    if (!hit || !hit.length) return; // someone else already dealt with this row
  } catch (e) {
    console.error("failRow update error:", e && e.message);
    note = "\n(I could not mark the row as failed; please check it in scheduled_posts.)";
  }
  console.error(`Scheduled post ${row.id} failed: ${reason}`);
  await alertChef(
    env,
    `⚠️ Aurion post NOT sent\nPost: ${rowTitle(row)}\nSlot: ${slot} (Lisbon)\nWhy: ${reason}\n` +
      (whatNow || "What now: the row is still in scheduled_posts, marked failed. Delete it, fix the content and schedule it again.") +
      note
  );
}

// Outage: count the try and put the row back for the next slot; after the last try, tell Chef.
async function retryOrFail(env, row, origStatus, slot, reason) {
  const tries = (Number(row.attempts) || 0) + 1;
  if (tries >= SCHED.maxTries) {
    await failRow(env, row, slot, `${reason} (gave up after ${SCHED.maxTries} tries)`);
    return;
  }
  console.error(`Scheduled post ${row.id}: try ${tries} of ${SCHED.maxTries} failed: ${reason}`);
  try {
    await patchRow(env, row, "&posting_status=eq.pending", {
      status: origStatus,
      attempts: tries,
      failure_reason: `Try ${tries} of ${SCHED.maxTries}: ${String(reason).slice(0, 300)}`,
      runner_locked_until: null,
      updated_at: new Date().toISOString(),
    });
  } catch (e) {
    console.error("retryOrFail update error:", e && e.message);
  }
}

function buildDashboardRecord(row, messageId, sentAtIso, mediaKind) {
  const pc = contentOf(row) || {};
  const f = (k) => row[k] || pc[k] || null;
  const chat = row.channel_group_id;
  const rec = {
    scheduled_post_id: row.id,
    social_platform: row.social_platform,
    post_content: row.post_content,
    external_post_id: messageId || "unknown",
    posted_at: sentAtIso,
    url: messageId ? `https://t.me/c/${String(chat).replace("-100", "")}/${messageId}` : row.url,
    channel_group_id: chat,
    thread_id: row.thread_id,
    character_profile: f("character_profile"),
    name: f("name"),
    username: f("username"),
    role: f("role"),
    character_avatar: f("character_avatar"),
    title: f("title"),
    description: f("description"),
    hashtags: f("hashtags"),
    keywords: f("keywords"),
    cta: f("cta"),
    theme: f("theme"),
    audience: f("audience"),
    voice_style: f("voice_style"),
    media_type: f("media_type"),
    template_type: f("template_type"),
    scheduled_date: row.scheduled_date,
    scheduled_time: row.scheduled_time,
    user_id: row.user_id,
    created_by: row.created_by,
    content_id: row.content_id,
    platform_id: row.platform_id,
    media_files: f("media_files"),
    selected_platforms: f("selected_platforms"),
    platform: row.platform,
    service_type: SCHED.lane,
    platform_icon: row.platform_icon,
    type: row.type,
  };
  // dashboard_posts requires these five; scheduled_posts does not. Safe values only when empty.
  if (!rec.theme) rec.theme = "general";
  if (!rec.audience) rec.audience = "community";
  if (!rec.media_type) rec.media_type = mediaKind ? (mediaKind === "photo" ? "image" : mediaKind) : "text";
  if (!rec.template_type) rec.template_type = "social_media";
  if (!rec.description) rec.description = rec.title || buildPostText(row, "plain").slice(0, 200) || "Posted by aurion-bot";
  // the proper "sent" labels
  Object.assign(rec, {
    post_status: "complete",
    posting_status: "sent",
    status: "complete",
    delivery_status: "sent",
    completed_at: sentAtIso,
    runner_name: SCHED.lane,
    run_by: SCHED.lane,
  });
  return Object.fromEntries(Object.entries(rec).filter(([, v]) => v !== null && v !== undefined));
}

// Everything after Telegram accepted the post. Nothing here can send again.
async function bookkeepSent(env, row, sendResult, slot, mediaKind) {
  const problems = [];
  const sentAt = new Date().toISOString();
  try {
    await patchRow(env, row, "", {
      posting_status: "sent",
      status: "complete",
      failure_reason: null,
      runner_locked_until: null,
      updated_at: sentAt,
    });
  } catch (e) {
    problems.push("the row could not be marked as sent");
    console.error("mark sent error:", e && e.message);
  }
  let saved = false;
  try {
    await sb(env, "dashboard_posts", {
      method: "POST",
      headers: { ...JSON_HEADERS, Prefer: "return=minimal" },
      body: JSON.stringify(buildDashboardRecord(row, sendResult.messageId, sentAt, mediaKind)),
    });
    saved = true;
  } catch (e) {
    problems.push("it could not be saved in dashboard_posts (" + String((e && e.message) || e).slice(0, 200) + ")");
    console.error("dashboard_posts insert error:", e && e.message);
  }
  if (saved) {
    try {
      await sb(env, `scheduled_posts?id=eq.${encodeURIComponent(row.id)}&service_type=eq.${SCHED.lane}`, { method: "DELETE" });
    } catch (e) {
      problems.push("it could not be removed from scheduled_posts (" + String((e && e.message) || e).slice(0, 200) + ")");
      console.error("scheduled_posts delete error:", e && e.message);
    }
  }
  const lines = [];
  if (problems.length) {
    lines.push(
      `⚠️ Aurion post SENT, but the housekeeping needs you\nPost: ${rowTitle(row)}\nSlot: ${slot} (Lisbon)\nThe post is in Telegram, but ${problems.join("; and ")}.\n` +
        (saved ? "What now: delete the row from scheduled_posts by hand." : "What now: the row stays in scheduled_posts (it will not be sent again). Move it to dashboard_posts by hand.")
    );
  }
  if (sendResult.plain) {
    lines.push(`ℹ️ Aurion post went out as PLAIN text (Telegram refused the formatting)\nPost: ${rowTitle(row)}\nSlot: ${slot} (Lisbon)\nCheck the ** * _ [] symbols in the text on the dashboard.`);
  }
  for (const l of lines) await alertChef(env, l);
}

// One claimed row: check, build, send, book. Failures go to failRow / retryOrFail.
async function processRow(env, row, origStatus, slot) {
  try {
    const chatId = row.channel_group_id;
    if (!chatId) return failRow(env, row, slot, "The row has no channel_group_id (where to post).");
    if (!row.post_content && !row.description && !row.title) return failRow(env, row, slot, "The row has no content (no post_content, title or description).");

    const m = threadFrom(row.thread_id);
    const media = pickMedia(row);
    if (media && media.error) return failRow(env, row, slot, media.error);

    const htmlText = buildPostText(row, "html");
    if (!htmlText && !media) return failRow(env, row, slot, "There is no text to post.");
    const len = visibleLength(htmlText);
    if (media && len > SCHED.captionMax) {
      return failRow(env, row, slot, `The text is ${len} characters. Telegram allows at most 1,024 when a picture, video or GIF is attached.`);
    }
    if (!media && len > SCHED.textMax) {
      return failRow(env, row, slot, `The text is ${len} characters. Telegram allows at most 4,096 in a text post.`);
    }

    let file = null;
    if (media) {
      const dl = await fetchMedia(media.url);
      if (dl.error) {
        return dl.outage ? retryOrFail(env, row, origStatus, slot, dl.error) : failRow(env, row, slot, dl.error);
      }
      const spec = MEDIA_SEND[media.kind];
      file = { field: spec.field, mime: spec.mime, bytes: dl.bytes, name: dl.name || spec.def };
    }

    const r = await deliverRow(env, row, chatId, m, media, file);
    if (!r.ok) {
      const why = `Telegram said: ${r.description}`;
      return isOutage(r) ? retryOrFail(env, row, origStatus, slot, why) : failRow(env, row, slot, why);
    }
    await bookkeepSent(env, row, r, slot, media ? media.kind : null);
  } catch (e) {
    console.error("processRow error:", (e && e.stack) || e);
    await retryOrFail(env, row, origStatus, slot, "Unexpected error: " + String((e && e.message) || e).slice(0, 200));
  }
}

function threadFrom(threadId) {
  const m = String(threadId || "").match(/(\d+)$/);
  return m ? parseInt(m[1], 10) : null;
}

async function runScheduled(env, event) {
  const nowMs = event && typeof event.scheduledTime === "number" ? event.scheduledTime : Date.now();
  const now = lisbonParts(nowMs);
  if (!SCHED.slots.includes(now.hm)) return; // not a posting slot: nothing to do, no log
  if (!dbConfigured(env) || !env.TELEGRAM_BOT_TOKEN) {
    console.error("Scheduled run skipped: the Worker is missing its Supabase or Telegram settings");
    await alertChef(env, `⚠️ Aurion scheduled run (${now.hm} Lisbon) did nothing: a required setting is missing in the Worker (Supabase address or key, or the bot token).`);
    return;
  }
  const nowStamp = wallStamp(now.date, now.time);
  const rows = await sb(
    env,
    `scheduled_posts?select=*&service_type=eq.${SCHED.lane}&posting_status=eq.pending&order=scheduled_date.asc&limit=100`
  );
  let sentCount = 0;
  for (const row of rows || []) {
    const postStamp = wallStamp(String(row.scheduled_date || "").slice(0, 10), row.scheduled_time);
    if (Number.isNaN(postStamp)) {
      await failRow(env, row, now.hm, "The scheduled date or time on the row cannot be read.");
      continue;
    }
    if (postStamp > nowStamp) continue; // not due yet

    if (row.status === "processing") {
      const lockedUntil = Date.parse(row.runner_locked_until || "");
      if (lockedUntil > Date.now()) continue; // another run is working on it right now
      // The lock ran out: a run stopped mid-send. Never send it again blindly.
      await failRow(
        env,
        row,
        now.hm,
        "A previous run stopped while sending this post, so I cannot tell whether it went out.",
        "What now: check the Telegram topic first. If it is there, delete the row. If not, delete it and schedule it again."
      );
      continue;
    }

    if (nowStamp - postStamp > SCHED.overdueMs) {
      await failRow(env, row, now.hm, `It was more than 24 hours late (scheduled ${String(row.scheduled_date).slice(0, 10)} ${String(row.scheduled_time).slice(0, 5)}), so I did not send it.`);
      continue;
    }

    if (sentCount >= SCHED.maxPerRun) break; // the rest wait for the next slot
    let claimed;
    try {
      claimed = await patchRow(env, row, "&posting_status=eq.pending&or=(status.is.null,status.neq.processing)", {
        status: "processing",
        runner_locked_until: new Date(Date.now() + SCHED.lockMinutes * 60000).toISOString(),
      });
    } catch (e) {
      console.error("claim error:", e && e.message);
      continue;
    }
    if (!claimed || !claimed.length) continue; // another run won this row
    sentCount++;
    await processRow(env, claimed[0], row.status || "scheduled", now.hm);
  }
}

// ---------- Entry point ----------

export default {
  async fetch(request, env, ctx) {
    try {
      const url = new URL(request.url);
      if (url.pathname !== "/telegram") return new Response("Not found", { status: 404 });
      if (request.method !== "POST") {
        return new Response("Method not allowed", { status: 405, headers: { Allow: "POST" } });
      }
      if (!env.TELEGRAM_WEBHOOK_SECRET || !env.TELEGRAM_BOT_TOKEN) {
        console.error("Worker is missing TELEGRAM_WEBHOOK_SECRET or TELEGRAM_BOT_TOKEN");
        return new Response("Service unavailable", { status: 503 });
      }
      const got = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
      if (!safeEqual(got, env.TELEGRAM_WEBHOOK_SECRET)) {
        return new Response("Unauthorized", { status: 401 });
      }
      let update = null;
      try {
        update = await request.json();
      } catch (e) {
        update = null;
      }
      if (update && typeof update === "object") {
        // Answer Telegram at once; do the real work afterwards so Telegram never re-sends.
        ctx.waitUntil(handleUpdate(env, update));
      }
      return new Response("OK", { status: 200 });
    } catch (e) {
      console.error("fetch error:", (e && e.stack) || e);
      return new Response("OK", { status: 200 });
    }
  },

  // Cloudflare Cron Triggers (the Worker's own timer). Not a web route: nobody can call it from outside.
  async scheduled(event, env, ctx) {
    ctx.waitUntil(
      runScheduled(env, event).catch(async (e) => {
        console.error("scheduled run error:", (e && e.stack) || e);
        await alertChef(env, "⚠️ Aurion scheduled run stopped with an error: " + String((e && e.message) || e).slice(0, 300));
      })
    );
  },
};
