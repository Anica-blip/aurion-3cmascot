import os
import logging
import random
import re
import asyncio
import json
from datetime import datetime, timezone, time
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

# Try to import supabase client and psycopg2 — we will support both REST (supabase-python)
# and direct Postgres (psycopg2) depending on environment variables provided.
SUPABASE_AVAILABLE = False
PSYCOPG2_AVAILABLE = False
try:
    from supabase import create_client, Client as SupabaseClient
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

# Basic envs
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Supabase / DB envs - we accept multiple naming conventions and support 2 modes:
#  - REST mode: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (preferred) or SUPABASE_URL + SUPABASE_KEY
#  - Direct Postgres mode: SUPABASE_DB_URL (postgres://...) + SUPABASE_SECRET_KEY (DB user password/connection)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")  # often postgres://...
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")  # if used with direct DB

# prefer REST service role if present; otherwise fallback to anon REST key; otherwise try direct Postgres
USE_MODE = None  # "rest_service", "rest_anon", "pg", None

supabase = None  # Supabase client if using REST
pg_conn = None   # psycopg2 connection if using direct DB

def init_db_clients():
    global supabase, pg_conn, USE_MODE

    # If SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY present -> REST service role (preferred)
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and SUPABASE_AVAILABLE:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            USE_MODE = "rest_service"
            logger.info("Supabase REST client initialized using SUPABASE_SERVICE_ROLE_KEY.")
            return
        except Exception as e:
            logger.error(f"Failed to init supabase REST client with service role: {e}")

    # If SUPABASE_URL + SUPABASE_KEY and supabase available -> REST anon
    if SUPABASE_URL and SUPABASE_KEY and SUPABASE_AVAILABLE:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            USE_MODE = "rest_anon"
            logger.info("Supabase REST client initialized using SUPABASE_KEY (anon).")
            return
        except Exception as e:
            logger.error(f"Failed to init supabase REST client with anon key: {e}")

    # If direct Postgres URL present and psycopg2 available -> connect
    # Accept common forms: postgres:// or postgresql://
    if SUPABASE_DB_URL and PSYCOPG2_AVAILABLE:
        try:
            # psycopg2 can accept a full DSN in SUPABASE_DB_URL
            pg_conn = psycopg2.connect(SUPABASE_DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
            # If a SECRET_KEY is required separately, it's usually included in the DB URL; if not, project may use it differently.
            USE_MODE = "pg"
            logger.info("Direct Postgres connection established using SUPABASE_DB_URL.")
            return
        except Exception as e:
            logger.error(f"Failed to connect via SUPABASE_DB_URL: {e}")

    # Last resort: if user provided SUPABASE_DB_URL but psycopg2 isn't installed, notify
    if SUPABASE_DB_URL and not PSYCOPG2_AVAILABLE:
        logger.warning("SUPABASE_DB_URL provided but psycopg2 is not available in the environment.")

    # Nothing configured
    USE_MODE = None
    logger.warning("No usable Supabase/Postgres credentials found; DB functionality will be disabled.")

# Initialize DB clients at import/startup
init_db_clients()

# ========== Helper wrappers for DB operations ==========
def run_pg_query(query, params=None, fetchone=False, fetchall=True):
    """
    Helper to run a synchronous query on pg_conn and return rows as list/dict.
    """
    if pg_conn is None:
        raise RuntimeError("Postgres connection is not initialized (pg_conn is None).")
    with pg_conn.cursor() as cur:
        cur.execute(query, params or ())
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return None

def supabase_select(table, select_clause="*", eq=None, ilike=None, limit=None):
    """
    Use supabase client to select; returns result object or raises.
    """
    if supabase is None:
        raise RuntimeError("Supabase REST client not initialized.")
    q = supabase.table(table).select(select_clause)
    if eq is not None:
        # eq is tuple (column, value)
        q = q.eq(eq[0], eq[1])
    if ilike is not None:
        # ilike is tuple (column, pattern)
        q = q.ilike(ilike[0], ilike[1])
    if limit:
        q = q.limit(limit)
    return q.execute()

# ========== Application-specific DB functions (use wrappers) ==========
def has_greeted(user_id):
    try:
        if USE_MODE == "pg":
            row = run_pg_query("SELECT user_id FROM public.greeted_users WHERE user_id = %s LIMIT 1", (user_id,), fetchone=True)
            return bool(row)
        elif USE_MODE in ("rest_service", "rest_anon"):
            res = supabase_select("greeted_users", select_clause="user_id", eq=("user_id", user_id), limit=1)
            return bool(getattr(res, "data", None))
        else:
            return False
    except Exception as e:
        logger.error(f"DB error in has_greeted: {e}")
        return False

def mark_greeted(user_id):
    try:
        if USE_MODE == "pg":
            run_pg_query("INSERT INTO public.greeted_users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,), fetchall=False)
            pg_conn.commit()
        elif USE_MODE in ("rest_service", "rest_anon"):
            supabase.table("greeted_users").insert({"user_id": user_id}).execute()
    except Exception as e:
        logger.error(f"DB error in mark_greeted: {e}")

def get_faq_answer(user_question):
    try:
        if USE_MODE == "pg":
            row = run_pg_query(
                "SELECT answer FROM public.faq WHERE question ILIKE %s LIMIT 1",
                (f"%{user_question}%",),
                fetchone=True
            )
            return row["answer"] if row else None
        elif USE_MODE in ("rest_service", "rest_anon"):
            # use ilike on question
            res = supabase_select("faq", select_clause="answer", ilike=("question", f"%{user_question}%"), limit=1)
            if getattr(res, "data", None):
                return res.data[0].get("answer")
            return None
        else:
            return None
    except Exception as e:
        logger.error(f"DB error in get_faq_answer: {e}")
        return None

async def fetch_faq_list():
    """Return list of dicts with id and question."""
    if USE_MODE == "pg":
        rows = run_pg_query("SELECT id, question FROM public.faq ORDER BY id")
        return rows or []
    elif USE_MODE in ("rest_service", "rest_anon"):
        res = supabase_select("faq", select_clause="id,question")
        return res.data or []
    else:
        return []

async def fetch_faq_answer_by_id(faq_id):
    if USE_MODE == "pg":
        row = run_pg_query("SELECT answer FROM public.faq WHERE id = %s LIMIT 1", (faq_id,), fetchone=True)
        return row["answer"] if row else None
    elif USE_MODE in ("rest_service", "rest_anon"):
        res = supabase_select("faq", select_clause="answer", eq=("id", faq_id), limit=1)
        return res.data[0]["answer"] if getattr(res, "data", None) else None
    else:
        return None

async def fetch_facts_list():
    if USE_MODE == "pg":
        rows = run_pg_query("SELECT fact FROM public.fact ORDER BY id")
        return [r["fact"] for r in (rows or [])]
    elif USE_MODE in ("rest_service", "rest_anon"):
        res = supabase_select("fact", select_clause="fact")
        return [r["fact"] for r in (res.data or [])]
    else:
        return []

async def fetch_resources_list():
    if USE_MODE == "pg":
        rows = run_pg_query("SELECT title, link FROM public.resources ORDER BY id")
        return rows or []
    elif USE_MODE in ("rest_service", "rest_anon"):
        res = supabase_select("resources", select_clause="title,link")
        return res.data or []
    else:
        return []

# ========== App logic (handlers) ==========
processing_messages = [
    "Hey Champ, give me a second to help you with that!",
    "Hang tight, Champ! Aurion's on it.",
    "One moment, Champ—let me work my magic.",
    "Just a sec, Champ! Let me get that sorted for you.",
]

SIGNOFF = 'Keep crushing it, Champ! Aurion'

WELCOME = (
    "Welcome to 3C Thread To Success –your ultimate space for personal transformation and growth. "
    "Whether you're dreaming big or taking small steps, we're here to help you think it, do it, and own it!\n\n"
    "You've just joined a vibrant community built to turn your life into a purpose-driven adventure —filled with clarity, confidence, and courage. 🌱\n\n"
    "💎 Here's something we believe in deeply:\n"
    "Every person is a diamond —even if you're still buried in the rough. Growth isn't about becoming someone else... "
    "it's about polishing what's already there. So take your time, trust the process, and shine brighter with every step.\n\n"
    "For everything you need, head over to:\n👉 https://anica-blip.github.io/3c-links/\n"
    "There you'll find our success links, tools, goal setting, challenges, and more. Or just send me a message —I'm Aurion, your guide along this journey.\n\n"
    "Together, we rise. Together, we polish. Together, we shine. 💫\n"
    "Let's embark on this adventure and make a difference —one gem at a time."
)

RULES_LINK = "https://t.me/c/2377255109/6/400"

def ensure_signoff_once(answer, signoff):
    pattern = r'[\s.]*' + re.escape(signoff) + r'[\s.]*$'
    answer = re.sub(pattern, '', answer.strip())
    if not answer.endswith(('.', '!', '?')):
        answer += '.'
    return answer + ' ' + signoff

async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if USE_MODE is None:
        await update.message.reply_text("Database not configured. Admins: check SUPABASE env vars.")
        return
    try:
        loop = asyncio.get_event_loop()
        faqs = await loop.run_in_executor(None, lambda: asyncio.run(fetch_faq_list()))
        # fetch_faq_list is async but returns quickly; for safety wrapped
        # If fetch_faq_list returns a coroutine handling above, adjust; simplest is to call directly:
    except Exception:
        # fallback synchronous call
        faqs = await fetch_faq_list()
    try:
        if not faqs:
            await update.message.reply_text(
                "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
            return
        keyboard = [
            [InlineKeyboardButton(q["question"], callback_data=f'faq_{q["id"]}')] for q in faqs
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a FAQ:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"FAQ handler error: {e}")
        await update.message.reply_text(f"🔴 FAQ ERROR:\n{e}\n\nType: {type(e).__name__}")

async def faq_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if USE_MODE is None:
        await update.callback_query.edit_message_text("Database not configured. Admins: check SUPABASE env vars.")
        return
    try:
        query = update.callback_query
        await query.answer()
        faq_id = query.data.replace('faq_', '')
        answer = await fetch_faq_answer_by_id(faq_id)
        await query.edit_message_text(answer or "No answer found.")
    except Exception as e:
        logger.error(f"FAQ button handler error: {e}")
        await update.callback_query.edit_message_text(
            f"🔴 FAQ BUTTON ERROR:\n{e}\n\nType: {type(e).__name__}"
        )

async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if USE_MODE is None:
        await update.message.reply_text("Database not configured. Admins: check SUPABASE env vars.")
        return
    try:
        facts = await fetch_facts_list()
        if facts:
            await update.message.reply_text(f"💎 Aurion Fact:\n{random.choice(facts)}")
        else:
            await update.message.reply_text(
                "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
    except Exception as e:
        logger.error(f"FACT handler error: {e}")
        await update.message.reply_text(f"🔴 FACT ERROR:\n{e}\n\nType: {type(e).__name__}")

async def resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if USE_MODE is None:
        await update.message.reply_text("Database not configured. Admins: check SUPABASE env vars.")
        return
    try:
        resources_list = await fetch_resources_list()
        if not resources_list:
            await update.message.reply_text(
                "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
            return
        msg_lines = [f"[{item['title']}]({item['link']})" for item in resources_list]
        await update.message.reply_text("Here are some resources:\n" + "\n".join(msg_lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"RESOURCES handler error: {e}")
        await update.message.reply_text(
            "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

# Other handlers (start, ask, keywords etc) follow same as before but use the DB wrappers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not has_greeted(user_id):
        await update.message.reply_text(WELCOME)
        mark_greeted(user_id)
    else:
        await update.message.reply_text(random.choice(processing_messages))

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Champ, you gotta ask a question after /ask!")
        return
    user_question = " ".join(context.args)
    await update.message.reply_text(random.choice(processing_messages))
    try:
        faq_answer = get_faq_answer(user_question)
        if faq_answer:
            answer = ensure_signoff_once(faq_answer, SIGNOFF)
        else:
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
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=300
            )
            answer = response.choices[0].message.content.strip()
            answer = ensure_signoff_once(answer, SIGNOFF)
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text(
            ensure_signoff_once(f"Sorry Champ, Aurion hit a snag getting your answer. Error details: {e}", SIGNOFF)
        )

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Check out our digital 3C /id card: https://anica-blip.github.io/3c-links/")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let me know exactly what you're looking for so that I can guide you.\n\n"
        "You can ask Aurion for tips, facts, or guidance. Try:\n"
        "/faq – Browse FAQs\n"
        "/fact – Get a random fact\n"
        "/resources – View resources\n"
        "/rules – View community rules\n"
        "/hashtags – Show hashtags\n"
        "/topics – Show topics\n"
        "/id – Get the 3C Links web app\n"
        "Or just type your question!"
    )

TOPICS_LIST = [
    ("Aurion Gems", "https://t.me/c/2377255109/138"),
    ("ClubHouse Chatroom", "https://t.me/c/2377255109/10"),
    ("ClubHouse News & Releases", "https://t.me/c/2377255109/6"),
    ("ClubHouse Notices", "https://t.me/c/2377255109/1"),
    ("Weekly Challenges", "https://t.me/c/2377255109/39"),
    ("ClubHouse Mini-Challenges", "https://t.me/c/2377255109/25"),
    ("ClubHouse Learning", "https://t.me/c/2377255109/12"),
    ("3C Evolution Badges", "https://t.me/c/2377255109/355"),
    ("3C LEVEL 1", "https://t.me/c/2377255109/342"),
    ("3C LEVEL 2", "https://t.me/c/2377255109/347"),
]

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_lines = []
    for idx, (title, url) in enumerate(TOPICS_LIST, 1):
        msg_lines.append(f"{idx}) [{title}]({url})")
    msg = "\n".join(msg_lines)
    await update.message.reply_text(msg, parse_mode="Markdown")

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
    await update.message.reply_text("Please press this /hashtags and the list below should be the response after pressing /hashtags")
    msg_lines = [f"[{title}]({link})" for title, link in HASHTAGS_LIST]
    msg = "\n".join(msg_lines)
    await update.message.reply_text(msg, parse_mode="Markdown")

def extract_message_thread_id(link):
    """Extracts the numeric thread ID from a Telegram topic link."""
    if link and isinstance(link, str):
        match = re.search(r'/c/\d+/(?P<topicid>\d+)', link)
        if match:
            return int(match.group('topicid'))
    return None

# ========== DB STATUS + whichsupabase (debug) ==========
async def dbstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reports what DB client returns for the faq and fact tables (non-secret)."""
    if USE_MODE is None:
        await update.message.reply_text("Supabase/DB client not configured (USE_MODE is None).")
        return

    def check_tables():
        out = {"mode": USE_MODE}
        try:
            if USE_MODE == "pg":
                # run simple queries
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
    """Reports which credential mode the running process is using (non-secret)."""
    mode = USE_MODE or "none"
    details = []
    if mode == "rest_service":
        details.append("Using Supabase REST with service role key (server-only).")
    elif mode == "rest_anon":
        details.append("Using Supabase REST with anon key.")
    elif mode == "pg":
        details.append("Using direct Postgres connection (psycopg2).")
    else:
        details.append("No DB client configured.")
    await update.message.reply_text("Supabase mode: " + mode + "\n" + "\n".join(details))

# ========== ERROR HANDLER ==========
async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if context.error:
        tb_str = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
        logger.error(f"Traceback:\n{tb_str}")
    else:
        logger.error("No exception information available (context.error is None)")

# ========== MAIN ==========
def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        logger.error("Missing TELEGRAM_BOT_TOKEN or OPENAI_API_KEY")
        return

    # Log which DB mode is active (non-secret)
    logger.info(f"Aurion starting. Supabase/DB USE_MODE={USE_MODE}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("faq", faq))
    app.add_handler(CallbackQueryHandler(faq_button, pattern="^faq_"))
    app.add_handler(CommandHandler("fact", fact))
    app.add_handler(CommandHandler("resources", resources))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hashtags", hashtags))
    app.add_handler(CommandHandler("topics", topics))
    # debug commands
    app.add_handler(CommandHandler("dbstatus", dbstatus))
    app.add_handler(CommandHandler("whichsupabase", whichsupabase))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: None))  # minimal stub for message handler
    app.add_error_handler(error_handler)

    logger.info("Aurion bot starting in interactive mode...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
