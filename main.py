import os
import logging
import random
import re
import asyncio
import json
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI
import traceback

# NOTE (2026-09-06 cleanup): scheduled_posts_runner is no longer imported/started here.
# Scheduled posting is handled entirely by the separate Render Cron Job
# ("scheduled-posts-processor", Node/render-cron.ts in the 3c-control-center repo).
# Running it a second time from inside this bot was leftover from an earlier setup
# and only added a way for the whole bot to crash if that module's own credential
# checks failed at import time. If scheduled_posts_runner.py is still needed for
# something else, it can stay in the repo unused — just no longer imported here.

# Optional imports for DB clients — try to import but handle missing libs gracefully.
SUPABASE_AVAILABLE = False
PSYCOPG2_AVAILABLE = False
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except Exception:
    SUPABASE_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except Exception:
    PSYCOPG2_AVAILABLE = False

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Three supported Supabase auth modes:
# 1) Direct Postgres: SUPABASE_DB_URL (postgres://...)
# 2) Service Role REST: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (bypasses RLS)
# 3) Anonymous REST: SUPABASE_URL + SUPABASE_ANON_KEY (has RLS restrictions)
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")
# SUPABASE_SECRET_KEY is intentionally kept even though it isn't read further down in
# this file — Chef confirmed (2026-09-06) this is part of an extra Supabase auth layer
# added on purpose beyond the anon key. Left alone, not removed.
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Telegram numeric user ID allowed to run admin/debug commands (/dbstatus, /whichsupabase,
# /testtables). This is a dedicated env var Chef adds in Render once she has her real
# Telegram numeric ID (from @userinfobot). Fails closed: locked for everyone, including
# Chef, until it's set.
ADMIN_USER_ID = (os.getenv("BOT_ADMIN_TELEGRAM_ID") or "").strip()

# Runtime vars
USE_MODE = None  # "pg", "rest_service", "rest_anon", or None
pg_conn = None
supabase = None

# Initialize OpenAI client as before (only used in /ask)
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def init_db_clients():
    global pg_conn, supabase, USE_MODE

    # DEBUG: Print what we have available
    print("=" * 60)
    print("DATABASE CONNECTION DIAGNOSTIC")
    print("=" * 60)
    print(f"SUPABASE_DB_URL: {'SET' if SUPABASE_DB_URL else 'NOT SET'}")
    print(f"SUPABASE_URL: {'SET' if SUPABASE_URL else 'NOT SET'}")
    print(f"SUPABASE_SERVICE_ROLE_KEY: {'SET' if SUPABASE_SERVICE_ROLE_KEY else 'NOT SET'}")
    print(f"SUPABASE_ANON_KEY: {'SET' if SUPABASE_ANON_KEY else 'NOT SET'}")
    print(f"PSYCOPG2_AVAILABLE: {PSYCOPG2_AVAILABLE}")
    print(f"SUPABASE_AVAILABLE: {SUPABASE_AVAILABLE}")
    print("=" * 60)

    # Prefer direct Postgres if DSN provided and psycopg2 available
    if SUPABASE_DB_URL and PSYCOPG2_AVAILABLE:
        print("Attempting Direct Postgres connection...")
        try:
            pg_conn = psycopg2.connect(SUPABASE_DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
            pg_conn.autocommit = False
            USE_MODE = "pg"
            logger.info("DB mode: direct Postgres (SUPABASE_DB_URL).")
            print("✅ SUCCESS: Connected via Direct Postgres")
            return
        except Exception as e:
            logger.error(f"Failed to connect with SUPABASE_DB_URL: {e}")
            print(f"❌ FAILED: Direct Postgres - {e}")

    # Try service role REST API first (bypasses RLS)
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and SUPABASE_AVAILABLE:
        print("Attempting Supabase REST API with SERVICE_ROLE_KEY...")
        try:
            # Python supabase-py automatically handles headers for SERVICE_ROLE_KEY
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            USE_MODE = "rest_service"
            logger.info("DB mode: Supabase REST service role (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY).")
            print("✅ SUCCESS: Connected via Supabase REST API (SERVICE ROLE)")
            return
        except Exception as e:
            logger.error(f"Failed to init supabase REST service role client: {e}")
            print(f"❌ FAILED: Supabase REST API (SERVICE ROLE) - {e}")

    # Fallback to anon REST if available
    if SUPABASE_URL and SUPABASE_ANON_KEY and SUPABASE_AVAILABLE:
        print("Attempting Supabase REST API with ANON_KEY...")
        try:
            # Python supabase-py automatically handles headers for ANON_KEY
            supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            USE_MODE = "rest_anon"
            logger.info("DB mode: Supabase REST anon (SUPABASE_URL + SUPABASE_ANON_KEY).")
            print("✅ SUCCESS: Connected via Supabase REST API (ANON)")
            return
        except Exception as e:
            logger.error(f"Failed to init supabase REST anon client: {e}")
            print(f"❌ FAILED: Supabase REST API (ANON) - {e}")

    USE_MODE = None
    logger.warning("No DB client configured: set SUPABASE_DB_URL or SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY/SUPABASE_ANON_KEY.")
    print("❌ RESULT: No DB client configured")
    print("=" * 60)

# Run initialization once
init_db_clients()

# ------- DB helper wrappers -------
def run_pg_query(query, params=None, fetchone=False, fetchall=True):
    if pg_conn is None:
        raise RuntimeError("Postgres connection not initialized.")
    with pg_conn.cursor() as cur:
        cur.execute(query, params or ())
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return None

def supabase_select(table, select_clause="*", eq=None, ilike=None, limit=None):
    if supabase is None:
        raise RuntimeError("Supabase client not initialized.")
    q = supabase.table(table).select(select_clause)
    if eq is not None:
        q = q.eq(eq[0], eq[1])
    if ilike is not None:
        q = q.ilike(ilike[0], ilike[1])
    if limit:
        q = q.limit(limit)
    return q.execute()

# ------- Synchronous DB functions used by handlers (called via executor) -------
def has_greeted_sync(user_id):
    try:
        if USE_MODE == "pg":
            row = run_pg_query("SELECT user_id FROM public.greeted_users WHERE user_id = %s LIMIT 1", (user_id,), fetchone=True)
            return bool(row)
        elif USE_MODE in ("rest_anon", "rest_service"):
            res = supabase_select("greeted_users", select_clause="user_id", eq=("user_id", user_id), limit=1)
            return bool(getattr(res, "data", None))
    except Exception as e:
        logger.error(f"has_greeted_sync error: {e}")
    return False

def mark_greeted_sync(user_id):
    try:
        if USE_MODE == "pg":
            run_pg_query("INSERT INTO public.greeted_users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,), fetchall=False)
            pg_conn.commit()
        elif USE_MODE in ("rest_anon", "rest_service"):
            supabase.table("greeted_users").insert({"user_id": user_id}).execute()
    except Exception as e:
        logger.error(f"mark_greeted_sync error: {e}")
        if USE_MODE == "pg":
            try:
                pg_conn.rollback()
            except:
                pass

def get_faq_answer_sync(user_question):
    try:
        if USE_MODE == "pg":
            row = run_pg_query("SELECT answer FROM public.faq WHERE question ILIKE %s LIMIT 1", (f"%{user_question}%",), fetchone=True)
            return row["answer"] if row else None
        elif USE_MODE in ("rest_anon", "rest_service"):
            res = supabase_select("faq", select_clause="answer", ilike=("question", f"%{user_question}%"), limit=1)
            if getattr(res, "data", None):
                return res.data[0].get("answer")
    except Exception as e:
        logger.error(f"get_faq_answer_sync error: {e}")
    return None

# NEW (2026-09-23): backup lookup for /ask, checked only when the faq table has no
# match. The `keyword` table (Control Center project) was created by Chef but never
# read by any code until now. Its `keyword` column can hold several comma-separated
# trigger words in one row (see id 7: "thank you, thanks, appreciate it"), so this
# checks each trigger as a whole-word, case-insensitive match against the user's
# question rather than the substring-of-a-full-question style /faq uses. When more
# than one trigger matches, the longest (most specific) one wins — e.g. "aurion
# vault" beats the standalone "aurion" keyword for "tell me about the aurion vault".
def get_keyword_answer_sync(user_question):
    try:
        if USE_MODE == "pg":
            rows = run_pg_query("SELECT keyword, answer FROM public.keyword")
        elif USE_MODE in ("rest_anon", "rest_service"):
            res = supabase_select("keyword", select_clause="keyword,answer")
            rows = res.data or []
        else:
            return None
    except Exception as e:
        logger.error(f"get_keyword_answer_sync error: {e}")
        return None

    best_answer = None
    best_len = 0
    for row in rows or []:
        answer = row.get("answer")
        raw_keywords = row.get("keyword")
        if not raw_keywords or not answer:
            continue
        for trigger in raw_keywords.split(","):
            trigger = trigger.strip()
            if not trigger:
                continue
            if re.search(r'\b' + re.escape(trigger) + r'\b', user_question, re.IGNORECASE):
                if len(trigger) > best_len:
                    best_len = len(trigger)
                    best_answer = answer
    return best_answer

def fetch_faq_list_sync():
    try:
        if USE_MODE == "pg":
            rows = run_pg_query("SELECT id, question FROM public.faq ORDER BY id")
            return rows or []
        elif USE_MODE in ("rest_anon", "rest_service"):
            res = supabase_select("faq", select_clause="id,question")
            return res.data or []
    except Exception as e:
        logger.error(f"fetch_faq_list_sync error: {e}")
    return []

def fetch_faq_answer_by_id_sync(faq_id):
    try:
        if USE_MODE == "pg":
            row = run_pg_query("SELECT answer FROM public.faq WHERE id = %s LIMIT 1", (faq_id,), fetchone=True)
            return row["answer"] if row else None
        elif USE_MODE in ("rest_anon", "rest_service"):
            res = supabase_select("faq", select_clause="answer", eq=("id", faq_id), limit=1)
            return res.data[0]["answer"] if getattr(res, "data", None) else None
    except Exception as e:
        logger.error(f"fetch_faq_answer_by_id_sync error: {e}")
    return None

def fetch_facts_list_sync():
    try:
        if USE_MODE == "pg":
            rows = run_pg_query("SELECT fact FROM public.fact ORDER BY id")
            return [r["fact"] for r in (rows or [])]
        elif USE_MODE in ("rest_anon", "rest_service"):
            res = supabase_select("fact", select_clause="fact")
            return [r["fact"] for r in (res.data or [])]
    except Exception as e:
        logger.error(f"fetch_facts_list_sync error: {e}")
    return []

# ------- Bot logic / handlers -------
processing_messages = [
    "Hey Champ, give me a second to help you with that!",
    "Hang tight, Champ! Aurion's on it.",
    "One moment, Champ—let me work my magic.",
    "Just a sec, Champ! Let me get that sorted for you.",
]

SIGNOFF = 'Keep crushing it, Champ! Aurion'

# UPDATED (2026-09-23): Chef rewrote the /start welcome — the old long version
# repeated the 3c-links plug that /id already covers, and was no longer a fit for
# where the community is now. New version is short and explains how /ask works,
# since that's the one thing newcomers most need spelled out. Sent with
# parse_mode="HTML" (see start() below) so the <u> tag actually underlines instead
# of showing as literal text.
WELCOME = (
    "Hey Champ, this is where our journey together begins! I'm here to guide you "
    "and help with anything community-related.\n\n"
    "Just remember to type /ask <u>followed by your question</u> whenever you want "
    "to talk to me. I don't listen in on conversations between members, so a little "
    "nudge is all it takes to get my attention.\n\n"
    + SIGNOFF
)

# Welcome/goodbye for people joining or leaving the group itself — separate from
# WELCOME above, which only fires on someone DMing /start to the bot.
WELCOME_NEW_MEMBER = (
    "Hey Champ, nice to have you join the 3C community! 🎉\n\n"
    "Take your time to explore around and ask me anything. "
    "You'll find the cards here in this folder to know how to speak to me — "
    "it's going to be fun getting to speak to you too.\n\n"
    + SIGNOFF
)

GOODBYE_MEMBER = (
    "Hey Champ, we hope you enjoyed your time with us. Welcome back anytime.\n\n"
    + SIGNOFF
)

RULES_LINK = "https://t.me/c/2377255109/6/400"

def ensure_signoff_once(answer, signoff):
    pattern = r'[\s.]*' + re.escape(signoff) + r'[\s.]*$'
    answer = re.sub(pattern, '', answer.strip())
    if not answer.endswith(('.', '!', '?')):
        answer += '.'
    return answer + ' ' + signoff

def is_admin(update: Update) -> bool:
    """Restricts admin/debug commands to Chef. Reads Telegram numeric user ID from
    BOT_ADMIN_TELEGRAM_ID. Fails closed: if it's not set yet, nobody can run these
    commands, including Chef, until it's configured."""
    if not ADMIN_USER_ID or not update.effective_user:
        return False
    return str(update.effective_user.id) == ADMIN_USER_ID

# Handlers use executor to call sync DB functions
async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if USE_MODE is None:
        await update.message.reply_text("Database not configured. Admins: check SUPABASE env vars.")
        return
    loop = asyncio.get_event_loop()
    try:
        faqs = await loop.run_in_executor(None, fetch_faq_list_sync)
    except Exception as e:
        logger.error(f"Error fetching FAQ list: {e}")
        faqs = []
    if not faqs:
        await update.message.reply_text("Sorry, Champ! Aurion can't fetch this right now due to technical issues.")
        return
    keyboard = [[InlineKeyboardButton(q["question"], callback_data=f'faq_{q["id"]}')] for q in faqs]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a FAQ:", reply_markup=reply_markup)

async def faq_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if USE_MODE is None:
        await update.callback_query.edit_message_text("Database not configured. Admins: check SUPABASE env vars.")
        return
    query = update.callback_query
    await query.answer()
    faq_id = query.data.replace('faq_', '')
    loop = asyncio.get_event_loop()
    try:
        answer = await loop.run_in_executor(None, fetch_faq_answer_by_id_sync, faq_id)
    except Exception as e:
        logger.error(f"Error fetching FAQ answer by id: {e}")
        answer = None
    await query.edit_message_text(answer or "No answer found.")

async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if USE_MODE is None:
        await update.message.reply_text("Database not configured. Admins: check SUPABASE env vars.")
        return
    loop = asyncio.get_event_loop()
    try:
        facts = await loop.run_in_executor(None, fetch_facts_list_sync)
    except Exception as e:
        logger.error(f"Error fetching facts: {e}")
        facts = []
    if facts:
        await update.message.reply_text(f"💎 Aurion Fact:\n{random.choice(facts)}")
    else:
        await update.message.reply_text("Sorry, Champ! Aurion can't fetch this right now due to technical issues.")

# Simple greeting/marking
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    loop = asyncio.get_event_loop()
    greeted = await loop.run_in_executor(None, has_greeted_sync, user_id)
    if not greeted:
        # UPDATED (2026-09-23): parse_mode="HTML" added so the <u> tag in WELCOME
        # renders as an actual underline instead of showing the raw tag text.
        await update.message.reply_text(WELCOME, parse_mode="HTML")
        await loop.run_in_executor(None, mark_greeted_sync, user_id)
    else:
        await update.message.reply_text(random.choice(processing_messages))

# Fires when someone joins the group itself (not the /start DM flow).
async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.new_chat_members:
        return
    thread_id = update.message.message_thread_id
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=WELCOME_NEW_MEMBER,
            message_thread_id=thread_id,
        )

# Fires when someone leaves/is removed from the group.
async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.left_chat_member:
        return
    member = update.message.left_chat_member
    if member.is_bot:
        return
    thread_id = update.message.message_thread_id
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=GOODBYE_MEMBER,
        message_thread_id=thread_id,
    )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Champ, you gotta ask a question after /ask!")
        return
    user_question = " ".join(context.args)
    await update.message.reply_text(random.choice(processing_messages))
    loop = asyncio.get_event_loop()
    try:
        faq_answer = await loop.run_in_executor(None, get_faq_answer_sync, user_question)
        if faq_answer:
            answer = ensure_signoff_once(faq_answer, SIGNOFF)
        else:
            # NEW (2026-09-23): keyword table checked as a backup before falling to
            # OpenAI — see get_keyword_answer_sync above.
            keyword_answer = await loop.run_in_executor(None, get_keyword_answer_sync, user_question)
            if keyword_answer:
                answer = ensure_signoff_once(keyword_answer, SIGNOFF)
            else:
                if not openai_client:
                    raise RuntimeError("OpenAI client not configured (OPENAI_API_KEY missing).")
                system_prompt = (
                    "You are Aurion, the 3C Mascot: energetic, motivating, a bit cheeky, and always supportive. "
                    "Reply in 1-2 short paragraphs. Vary your phrasing for returning users. "
                    "After your answer, always add this signoff, no line break, just space after the last full stop: "
                    "'Keep crushing it, Champ! Aurion'"
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ]
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=300
                )
                answer = response.choices[0].message.content.strip()
                answer = ensure_signoff_once(answer, SIGNOFF)
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"Ask handler error: {e}")
        await update.message.reply_text(ensure_signoff_once(f"Sorry Champ, Aurion hit a snag getting your answer. Error details: {e}", SIGNOFF))

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Check out our digital 3C /id card: https://anica-blip.github.io/3c-links/")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 Community Rules: https://t.me/c/2377255109/6/400")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "You can ask Aurion for tips, facts, or guidance. Try:\n"
        "/faq – Browse FAQs\n"
        "/fact – Get a random fact\n"
        "/rules – View community rules\n"
        "/id – Get the 3C Links web app\n"
    )

TOPICS_LIST = [
    ("Aurion Gems", "https://t.me/c/2377255109/138"),
    ("ClubHouse Chatroom", "https://t.me/c/2377255109/10"),
    ("ClubHouse News & Releases", "https://t.me/c/2377255109/6"),
    ("ClubHouse Notices", "https://t.me/c/2377255109/674"),
    ("Weekly Challenges", "https://t.me/c/2377255109/39"),
    ("ClubHouse Mini-Challenges", "https://t.me/c/2377255109/25"),
    ("ClubHouse Learning", "https://t.me/c/2377255109/12"),
]

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_lines = [f"{idx+1}) [{t}]({u})" for idx,(t,u) in enumerate(TOPICS_LIST)]
    await update.message.reply_text("\n".join(msg_lines), parse_mode="Markdown")

HASHTAGS_LIST = [
    ("#Topics", "https://t.me/c/2431571054/58"),
    ("#Blog", "https://t.me/c/2431571054/58"),
    ("#Provisions", "https://t.me/c/2431571054/58"),
    ("#Training", "https://t.me/c/2431571054/58"),
    ("#Knowledge", "https://t.me/c/2431571054/58"),
    ("#Language", "https://t.me/c/2431571054/58"),
    ("#Audiobook", "https://t.me/c/2431571054/58"),
    ("#Healingmusic", "https://t.me/c/2431571054/58"),
]

async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_lines = [f"[{title}]({link})" for title, link in HASHTAGS_LIST]
    await update.message.reply_text("\n".join(msg_lines), parse_mode="Markdown")

def extract_message_thread_id(link):
    if link and isinstance(link, str):
        match = re.search(r'/c/\d+/(?P<topicid>\d+)', link)
        if match:
            return int(match.group('topicid'))
    return None

# Debug commands — gated to Chef only. Previously any group member could run these
# and see raw DB status/sample data; that's why they're gated now.
async def dbstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("This command is only available to the Aurion team, Champ.")
        return
    if USE_MODE is None:
        await update.message.reply_text("DB client not configured (USE_MODE is None).")
        return
    def check_tables():
        out = {"mode": USE_MODE}
        try:
            if USE_MODE == "pg":
                out["faq_sample"] = run_pg_query("SELECT id, question FROM public.faq LIMIT 1", fetchall=True)
                out["fact_sample"] = run_pg_query("SELECT id, fact FROM public.fact LIMIT 1", fetchall=True)
            else:
                res1 = supabase_select("faq", select_clause="id,question", limit=1)
                out["faq_sample"] = {"data": getattr(res1, "data", None), "error": getattr(res1, "error", None)}
                res2 = supabase_select("fact", select_clause="id,fact", limit=1)
                out["fact_sample"] = {"data": getattr(res2, "data", None), "error": getattr(res2, "error", None)}
        except Exception as e:
            out["exception"] = str(e)
        return out
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, check_tables)
    text = json.dumps(result, default=str, indent=2)
    if len(text) > 3800:
        text = text[:3800] + "\n\n...[truncated]"
    await update.message.reply_text("DB status:\n" + text)

async def whichsupabase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("This command is only available to the Aurion team, Champ.")
        return
    mode = USE_MODE or "none"
    desc = {
        "pg": "Direct Postgres (SUPABASE_DB_URL)",
        "rest_service": "Supabase REST (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)",
        "rest_anon": "Supabase REST (SUPABASE_URL + SUPABASE_ANON_KEY)",
        "none": "No DB client configured"
    }.get(mode, mode)
    await update.message.reply_text(f"Supabase mode: {mode}\n{desc}")

async def test_tables(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct test of Supabase client queries on faq and fact tables"""
    if not is_admin(update):
        await update.message.reply_text("This command is only available to the Aurion team, Champ.")
        return
    if USE_MODE is None:
        await update.message.reply_text("❌ No DB client configured (USE_MODE is None)")
        return

    if USE_MODE == "pg":
        await update.message.reply_text("⚠️ Using Direct Postgres - use /dbstatus instead")
        return

    results = []
    results.append(f"🔍 Testing Supabase REST API queries\n")
    results.append(f"Mode: {USE_MODE}\n")
    results.append(f"="*40 + "\n")

    # Test FAQ table
    try:
        results.append("Testing 'faq' table...\n")
        response = supabase.table("faq").select("*").limit(1).execute()
        results.append(f"✅ FAQ SUCCESS\n")
        results.append(f"Data: {response.data}\n")
        results.append(f"Count: {response.count}\n")
    except Exception as e:
        results.append(f"❌ FAQ FAILED\n")
        results.append(f"Error: {str(e)}\n")
        results.append(f"Type: {type(e).__name__}\n")

    results.append(f"\n" + "="*40 + "\n")

    # Test FACT table
    try:
        results.append("Testing 'fact' table...\n")
        response = supabase.table("fact").select("*").limit(1).execute()
        results.append(f"✅ FACT SUCCESS\n")
        results.append(f"Data: {response.data}\n")
        results.append(f"Count: {response.count}\n")
    except Exception as e:
        results.append(f"❌ FACT FAILED\n")
        results.append(f"Error: {str(e)}\n")
        results.append(f"Type: {type(e).__name__}\n")

    message = "".join(results)
    if len(message) > 4000:
        message = message[:4000] + "\n\n...[truncated]"

    await update.message.reply_text(message)

# Error handler
async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if context.error:
        tb_str = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
        logger.error(f"Traceback:\n{tb_str}")

# Main
def main():
    if not TELEGRAM_TOKEN:
        logger.error("Missing TELEGRAM_BOT_TOKEN")
        return
    if not OPENAI_API_KEY:
        # Missing OpenAI key used to abort the entire bot at startup. It's only
        # needed for the /ask AI fallback (FAQ matches and every other command work
        # without it), so this is now just a warning.
        logger.warning("OPENAI_API_KEY not set — /ask will only be able to use FAQ matches, no AI fallback.")

    logger.info(f"Aurion starting. USE_MODE={USE_MODE}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("faq", faq))
    app.add_handler(CallbackQueryHandler(faq_button, pattern="^faq_"))
    app.add_handler(CommandHandler("fact", fact))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hashtags", hashtags))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("dbstatus", dbstatus))
    app.add_handler(CommandHandler("whichsupabase", whichsupabase))
    app.add_handler(CommandHandler("testtables", test_tables))
    # Join/leave greeting handlers — registered before the generic text handler
    # below so they get first look at those service messages.
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: None))
    app.add_error_handler(error_handler)

    # NOTE: scheduled_posts_runner is no longer started here — see the note at the
    # top of this file. Scheduled posting is handled by the separate Render Cron
    # Job in the 3c-control-center repo.

    logger.info("Aurion bot starting in interactive mode...")
    app.run_polling()

if __name__ == "__main__":
    main()
