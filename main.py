import os
import logging
import random
import re
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
from supabase import create_client, Client
import traceback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GROUP_POST_TARGETS = {
    "group 1": {"chat_id": -1002393705231},
    "group 2": {"chat_id": -1002377255109},
    "channel 1": {"chat_id": -1002431571054},
}

AURION_CONTENT_CENTER_CHAT_ID = -1002471721022  # Aurion 3C Mascot Playground channel
ADMIN_USER_IDS = {1377419565}  # <-- Replace with your Telegram user ID

processing_messages = [
    "Hey Champ, give me a second to help you with that!",
    "Hang tight, Champ! Aurion's on it.",
    "One moment, Champ—let me work my magic.",
    "Just a sec, Champ! Let me get that sorted for you.",
]

SIGNOFF = 'Keep crushing it, Champ! Aurion'

WELCOME = (
    "Welcome to 3C Thread To Success –your ultimate space for personal transformation and growth. "
    "Whether you're dreaming big or taking small steps, we’re here to help you think it, do it, and own it!\n\n"
    "You've just joined a vibrant community built to turn your life into a purpose-driven adventure —filled with clarity, confidence, and courage. 🌱\n\n"
    "💎 Here’s something we believe in deeply:\n"
    "Every person is a diamond —even if you're still buried in the rough. Growth isn’t about becoming someone else... "
    "it’s about polishing what’s already there. So take your time, trust the process, and shine brighter with every step.\n\n"
    "For everything you need, head over to:\n👉 https://anica-blip.github.io/3c-links/\n"
    "There you’ll find our success links, tools, goal setting, challenges, and more. Or just send me a message —I’m Aurion, your guide along this journey.\n\n"
    "Together, we rise. Together, we polish. Together, we shine. 💫\n"
    "Let’s embark on this adventure and make a difference —one gem at a time."
)

FAREWELL = (
    "Sad to see you go. Remember, you’re always welcome back. "
    "Stay strong and focused on polishing your diamond. 💎🔥"
)

RULES_LINK = "https://t.me/c/2377255109/6/400"

def ensure_signoff_once(answer, signoff):
    pattern = r'[\s.]*' + re.escape(signoff) + r'[\s.]*$'
    answer = re.sub(pattern, '', answer.strip())
    if not answer.endswith(('.', '!', '?')):
        answer += '.'
    return answer + ' ' + signoff

def has_greeted(user_id):
    try:
        result = supabase.table("greeted_users").select("user_id").eq("user_id", user_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Supabase error in has_greeted: {e}")
        return False

def mark_greeted(user_id):
    try:
        supabase.table("greeted_users").insert({"user_id": user_id}).execute()
    except Exception as e:
        logger.error(f"Supabase error in mark_greeted: {e}")

def get_faq_answer(user_question):
    try:
        result = supabase.table("faq").select("answer").ilike("question", f"%{user_question}%").execute()
        if len(result.data) > 0:
            return result.data[0]['answer']
        return None
    except Exception as e:
        logger.error(f"Supabase error in get_faq_answer: {e}")
        return None

async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = supabase.table("faq").select("id,question").execute()
        faqs = data.data or []
        if not faqs:
            await update.message.reply_text(
                "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
            return
        keyboard = [
            [InlineKeyboardButton(q["question"], callback_data=f'faq_{q["id"]}')] for q in faqs
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a FAQ:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Supabase FAQ error: {e}")
        await update.message.reply_text(
            "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

async def faq_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        faq_id = query.data.replace('faq_', '')
        data = supabase.table("faq").select("answer").eq("id", faq_id).single().execute()
        answer = data.data['answer'] if data.data else "No answer found."
        await query.edit_message_text(answer)
    except Exception as e:
        logger.error(f"Supabase FAQ button error: {e}")
        await update.callback_query.edit_message_text(
            "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = supabase.table("fact").select("fact").execute()
        facts = [item['fact'] for item in data.data] if data.data else []
        if facts:
            await update.message.reply_text(f"💎 Aurion Fact:\n{random.choice(facts)}")
        else:
            await update.message.reply_text(
                "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
    except Exception as e:
        logger.error(f"Supabase fact error: {e}")
        await update.message.reply_text(
            "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

async def resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = supabase.table("resources").select("title,link").execute()
        resources_list = data.data or []
        if not resources_list:
            await update.message.reply_text(
                "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
            return
        msg_lines = [f"[{item['title']}]({item['link']})" for item in resources_list]
        await update.message.reply_text("Here are some resources:\n" + "\n".join(msg_lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Supabase resources error: {e}")
        await update.message.reply_text(
            "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Community Rules: {RULES_LINK}")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        await update.message.reply_text(WELCOME)

async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    left_member = update.message.left_chat_member
    if not left_member.is_bot:
        await update.message.reply_text(FAREWELL)

KEYWORD_RESPONSES = [
    ("help", "If you need a hand, just type /ask followed by your question! Aurion's got your back."),
    ("motivate", "You’re stronger than you think, Champ! Every step counts."),
    ("thanks", "Anytime, Champ! Let’s keep that good energy rolling!"),
]

async def keyword_responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    for keyword, response in KEYWORD_RESPONSES:
        if keyword in text:
            await update.message.reply_text(response)
            break

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not has_greeted(user_id):
        await update.message.reply_text(WELCOME)
        mark_greeted(user_id)
    else:
        await update.message.reply_text(
            random.choice(processing_messages)
        )

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

def parse_targets_from_message(text):
    """
    Looks for a line like '/to group 1, channel 1' at the start of message or caption.
    Returns a set of channel keys e.g. {"group 1", "channel 1"}
    If none found, returns None (meaning: send to all).
    """
    if not text:
        return None
    m = re.match(r'^\/to\s+(.+)', text.strip(), re.IGNORECASE)
    if m:
        targets = {t.strip().lower() for t in m.group(1).split(",")}
        return targets
    return None

async def content_center_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # --- Robust null checks to avoid AttributeError ---
    if not update.effective_chat or not update.effective_user:
        logger.warning("Update missing effective_chat or effective_user: %r", update)
        return

    if update.effective_chat.id != AURION_CONTENT_CENTER_CHAT_ID:
        return
    if update.effective_user.id not in ADMIN_USER_IDS:
        if update.message:
            await update.message.reply_text("Sorry, only admins can trigger Aurion reposting.")
        return

    message = update.message
    if not message:
        logger.warning("No message in update for content_center_listener: %r", update)
        return

    text = message.text or message.caption or ""
    targets = parse_targets_from_message(text)
    # Remove the '/to ...' line from text/caption if present
    if targets:
        text = re.sub(r'^\/to\s+.+(\n|$)', '', text, flags=re.IGNORECASE).lstrip()

    # Decide where to post
    if targets:
        chosen_targets = {k: v for k, v in GROUP_POST_TARGETS.items() if k.lower() in targets}
    else:
        chosen_targets = GROUP_POST_TARGETS

    results = []
    for group_key, target in chosen_targets.items():
        # If photo(s) exist
        if message.photo:
            largest_photo = message.photo[-1].file_id
            await context.bot.send_photo(
                chat_id=target["chat_id"],
                photo=largest_photo,
                caption=text if text else None
            )
            results.append(f"Photo to {group_key}")
        # If video exists
        elif message.video:
            await context.bot.send_video(
                chat_id=target["chat_id"],
                video=message.video.file_id,
                caption=text if text else None
            )
            results.append(f"Video to {group_key}")
        # If document exists
        elif message.document:
            await context.bot.send_document(
                chat_id=target["chat_id"],
                document=message.document.file_id,
                caption=text if text else None
            )
            results.append(f"Document to {group_key}")
        # If just text
        elif text:
            await context.bot.send_message(
                chat_id=target["chat_id"],
                text=text
            )
            results.append(f"Text to {group_key}")

    if message:
        await message.reply_text("Aurion posted:\n" + "\n".join(results) if results else "Nothing sent.")

# The rest of your scheduled job, admin commands, and error handling is unchanged below...

async def send_due_messages_job(context: ContextTypes.DEFAULT_TYPE):
    now_utc = datetime.now(timezone.utc)
    slot_start = now_utc.replace(second=0, microsecond=0)
    slot_end = slot_start.replace(second=59, microsecond=999999)
    slot_start_str = slot_start.isoformat()
    slot_end_str = slot_end.isoformat()
    logger.info(f"[SCHEDULED JOB] Triggered at {now_utc.isoformat()}")
    logger.info(f"[SCHEDULED JOB] Slot window: {slot_start_str} to {slot_end_str}")

    try:
        result = supabase.table("message") \
            .select("*") \
            .gte("scheduled_at", slot_start_str) \
            .lte("scheduled_at", slot_end_str) \
            .is_("sent", False) \
            .execute()
        messages = result.data or []
        logger.info(f"[SCHEDULED JOB] Found {len(messages)} messages scheduled in this slot")
        logger.info(f"[SCHEDULED JOB] Fetched messages: {messages}")
    except Exception as e:
        logger.error(f"[SCHEDULED JOB] Supabase error: {e}")
        return

    if not messages:
        logger.info("[SCHEDULED JOB] No due messages to send in this slot.")
        return

    for msg in messages:
        group_key = msg.get("group_channel")
        post_target = GROUP_POST_TARGETS.get(group_key)
        content = msg.get("content")
        msg_id = msg.get("id")
        chat_id = post_target["chat_id"] if post_target else None
        thread_link = msg.get("thread_id")
        message_thread_id = extract_message_thread_id(thread_link)

        logger.info(f"[SCHEDULED JOB] Processing message id={msg_id}, group_channel={group_key}, chat_id={chat_id}, thread_link={thread_link}, message_thread_id={message_thread_id}, content={content!r}")
        if not post_target or not content:
            logger.error(f"[SCHEDULED JOB] Skipping message id={msg_id}: missing group_channel or content")
            continue
        try:
            if message_thread_id:
                await context.bot.send_message(chat_id=chat_id, text=content, message_thread_id=message_thread_id)
            else:
                await context.bot.send_message(chat_id=chat_id, text=content)
            logger.info(f"[SCHEDULED JOB] Sent message id={msg_id} to chat_id={chat_id}, message_thread_id={message_thread_id}")
        except Exception as e:
            logger.error(f"[SCHEDULED JOB] Failed to send message id={msg_id}: {e}")
            continue
        try:
            result = supabase.table("message").update({"sent": True}).eq("id", msg_id).execute()
            logger.info(f"[SCHEDULED JOB] Update result for id={msg_id}: {result.data}")
            if not result.data:
                logger.error(f"[SCHEDULED JOB] Update failed for id={msg_id}. Check field types, RLS, and permissions.")
        except Exception as e:
            logger.error(f"[SCHEDULED JOB] Update exception for id={msg_id}: {e}")

from datetime import timezone as dt_timezone

def schedule_daily_jobs(job_queue):
    times = [
        time(8, 0, tzinfo=timezone.utc),
        time(12, 0, tzinfo=timezone.utc),
        time(17, 0, tzinfo=timezone.utc),
        time(21, 0, tzinfo=timezone.utc)
    ]
    for t in times:
        job_queue.run_daily(send_due_messages_job, t, days=(0,1,2,3,4,5,6))
    logger.info("[SCHEDULER] Jobs scheduled for 08:00, 12:00, 17:00, 21:00 UTC (every day, UTC aware)")

async def sendnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now_utc = datetime.now(timezone.utc)
    now_utc_str = now_utc.isoformat()
    try:
        result = supabase.table("message").select("*").lte("scheduled_at", now_utc_str).is_("sent", False).execute()
        messages = result.data or []
    except Exception as e:
        logger.error(f"[SENDNOW] Supabase error: {e}")
        await update.message.reply_text("Sorry Champ, error fetching messages.")
        return

    if not messages:
        await update.message.reply_text("No pending posts to send.")
        return

    for msg in messages:
        group_key = msg.get("group_channel")
        post_target = GROUP_POST_TARGETS.get(group_key)
        content = msg.get("content")
        msg_id = msg.get("id")
        chat_id = post_target["chat_id"] if post_target else None
        thread_link = msg.get("thread_id")
        message_thread_id = extract_message_thread_id(thread_link)
        if not post_target or not content:
            continue
        try:
            if message_thread_id:
                await context.bot.send_message(chat_id=chat_id, text=content, message_thread_id=message_thread_id)
            else:
                await context.bot.send_message(chat_id=chat_id, text=content)
        except Exception as e:
            logger.error(f"[SENDNOW] Failed to send message id={msg_id}: {e}")
            continue
        try:
            supabase.table("message").update({"sent": True}).eq("id", msg_id).execute()
        except Exception as e:
            logger.error(f"[SENDNOW] Update exception for id={msg_id}: {e}")

    await update.message.reply_text("All pending posts delivered.")

async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if context.error:
        tb_str = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
        logger.error(f"Traceback:\n{tb_str}")
        print("Exception while handling an update:", context.error)
        print(tb_str)
    else:
        logger.error("No exception information available (context.error is None)")
        print("No exception information available (context.error is None)")

def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("One or more environment variables not set (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY).")
        print("One or more environment variables not set (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY).")
        return

    import time as pytime
    from datetime import datetime
    print("Server local time:", pytime.strftime("%Y-%m-%d %H:%M:%S", pytime.localtime()))
    print("Server UTC time:", pytime.strftime("%Y-%m-%d %H:%M:%S", pytime.gmtime()))
    print("Python datetime.now():", datetime.now())
    print("Python datetime.now(timezone.utc):", datetime.now(timezone.utc))
    print("TZ environment variable:", os.environ.get("TZ"))

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("faq", faq))
    app.add_handler(CallbackQueryHandler(faq_button, pattern="^faq_"))
    app.add_handler(CommandHandler("fact", fact))
    app.add_handler(CommandHandler("resources", resources))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hashtags", hashtags))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, keyword_responder))
    app.add_handler(CommandHandler("sendnow", sendnow))
    # The universal content-center handler:
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) & filters.Chat(AURION_CONTENT_CENTER_CHAT_ID),
        content_center_listener
    ))
    app.add_error_handler(error_handler)

    schedule_daily_jobs(app.job_queue)
    print("Aurion is polling. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
