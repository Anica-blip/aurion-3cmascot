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
// The one admin command (/dbstatus) is gated by the Telegram numeric id in
// BOT_ADMIN_TELEGRAM_ID and fails closed: if that secret is not set, nobody can run it.
//
// SECRETS (Cloudflare: Settings > Variables and Secrets, type "Secret"):
//   TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, OPENAI_API_KEY,
//   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, BOT_ADMIN_TELEGRAM_ID
//
// SUPABASE: 3C Control Center project, REST + service key only. Tables: faq, fact,
//   keyword, greeted_users (column telegram_user_id).
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
  "askFailure": "Champ, give me a moment, we're having some tech issues right now. Aurion is on it, so please try again in a little while."
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

async function askOpenAI(env, question) {
  if (!env.OPENAI_API_KEY) throw new Error("OpenAI client not configured (OPENAI_API_KEY missing).");
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${env.OPENAI_API_KEY}` },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: T.openaiSystemPrompt },
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
};
