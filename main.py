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
    JobQueue,
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

# Updated group targets - adjust these chat IDs to your actual groups
GROUP_POST_TARGETS = {
    "group 1": {"chat_id": -1002393705231},
    "group 2": {"chat_id": -1002377255109},
}

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

FAREWELL = (
    "Sad to see you go. Remember, you're always welcome back. "
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
                "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
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
            "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
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
            "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = supabase.table("fact").select("fact").execute()
        facts = [item['fact'] for item in data.data] if data.data else []
        if facts:
            await update.message.reply_text(f"💎 Aurion Fact:\n{random.choice(facts)}")
        else:
            await update.message.reply_text(
                "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
    except Exception as e:
        logger.error(f"Supabase fact error: {e}")
        await update.message.reply_text(
            "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

async def resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = supabase.table("resources").select("title,link").execute()
        resources_list = data.data or []
        if not resources_list:
            await update.message.reply_text(
                "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
            return
        msg_lines = [f"[{item['title']}]({item['link']})" for item in resources_list]
        await update.message.reply_text("Here are some resources:\n" + "\n".join(msg_lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Supabase resources error: {e}")
        await update.message.reply_text(
            "Sorry, Champ! Aurion can't fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
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
    ("motivate", "You're stronger than you think, Champ! Every step counts."),
    ("thanks", "Anytime, Champ! Let's keep that good energy rolling!"),
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

# ========== MAIN CHANGE: Using scheduled_posts table instead of message table ==========
async def send_scheduled_posts(context: ContextTypes.DEFAULT_TYPE = None):
    """Main function for cron job - sends posts scheduled for current time
    Can be called as a job callback (with context) or standalone"""
    now_utc = datetime.now(timezone.utc)
    # Round to current minute for precise matching
    current_minute = now_utc.replace(second=0, microsecond=0)
    next_minute = current_minute.replace(minute=current_minute.minute + 1)
    
    current_time_str = current_minute.isoformat()
    next_time_str = next_minute.isoformat()
    
    logger.info(f"[AUTO-SCHEDULER] Running at {now_utc.isoformat()}")
    logger.info(f"[AUTO-SCHEDULER] Looking for posts scheduled between {current_time_str} and {next_time_str}")

    try:
        # Query scheduled_posts table for posts due now
        result = supabase.table("scheduled_posts") \
            .select("*") \
            .gte("scheduled_time", current_time_str) \
            .lt("scheduled_time", next_time_str) \
            .eq("status", "scheduled") \
            .execute()
        
        posts = result.data or []
        logger.info(f"[AUTO-SCHEDULER] Found {len(posts)} posts scheduled for this time")
        
    except Exception as e:
        logger.error(f"[AUTO-SCHEDULER] Supabase error: {e}")
        return

    if not posts:
        logger.info("[AUTO-SCHEDULER] No scheduled posts found for current time")
        return

    # Use the application from context if available, otherwise create one
    if context and context.application:
        app = context.application
    else:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    for post in posts:
        try:
            await send_single_post(app, post)
        except Exception as e:
            logger.error(f"[AUTO-SCHEDULER] Failed to process post {post.get('id')}: {e}")

async def send_single_post(app, post):
    """Send a single scheduled post"""
    post_id = post.get("id")
    content = post.get("content")
    target_group = post.get("target_group", "").lower()
    target_thread = post.get("target_thread")
    character_name = post.get("character_name", "Aurion")
    
    logger.info(f"[CRON JOB] Processing post {post_id}: target_group={target_group}, character={character_name}")
    
    if not content:
        logger.error(f"[CRON JOB] Post {post_id} has no content, skipping")
        return
    
    # Map target_group to chat_id
    chat_id = None
    if "group 1" in target_group or "1" in target_group:
        chat_id = GROUP_POST_TARGETS["group 1"]["chat_id"]
    elif "group 2" in target_group or "2" in target_group:
        chat_id = GROUP_POST_TARGETS["group 2"]["chat_id"]
    
    if not chat_id:
        logger.error(f"[CRON JOB] Post {post_id}: Unknown target_group '{target_group}', skipping")
        return
    
    # Extract thread ID if specified
    message_thread_id = None
    if target_thread:
        message_thread_id = extract_message_thread_id(target_thread)
    
    try:
        # Send the message
        if message_thread_id:
            await app.bot.send_message(
                chat_id=chat_id, 
                text=content, 
                message_thread_id=message_thread_id
            )
            logger.info(f"[CRON JOB] Sent post {post_id} to chat {chat_id}, thread {message_thread_id}")
        else:
            await app.bot.send_message(chat_id=chat_id, text=content)
            logger.info(f"[CRON JOB] Sent post {post_id} to chat {chat_id}")
        
        # Mark as sent in database
        supabase.table("scheduled_posts") \
            .update({
                "status": "sent", 
                "sent_at": datetime.now(timezone.utc).isoformat()
            }) \
            .eq("id", post_id) \
            .execute()
            
        logger.info(f"[CRON JOB] Successfully updated post {post_id} status to 'sent'")
        
    except Exception as e:
        logger.error(f"[CRON JOB] Failed to send post {post_id}: {e}")
        # Mark as failed
        try:
            supabase.table("scheduled_posts") \
                .update({
                    "status": "failed",
                    "error_message": str(e)[:500]  # Limit error message length
                }) \
                .eq("id", post_id) \
                .execute()
        except Exception as update_error:
            logger.error(f"[CRON JOB] Failed to update error status for post {post_id}: {update_error}")

# ========== MANUAL TRIGGER for testing ==========
async def sendnow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual command to send all pending scheduled posts"""
    now_utc = datetime.now(timezone.utc)
    
    try:
        # Get all posts that should have been sent by now
        result = supabase.table("scheduled_posts") \
            .select("*") \
            .lte("scheduled_time", now_utc.isoformat()) \
            .eq("status", "scheduled") \
            .execute()
        
        posts = result.data or []
        
    except Exception as e:
        logger.error(f"[SENDNOW] Supabase error: {e}")
        await update.message.reply_text("Sorry Champ, error fetching scheduled posts.")
        return

    if not posts:
        await update.message.reply_text("No pending posts found to send.")
        return

    sent_count = 0
    for post in posts:
        try:
            await send_single_post(context.application, post)
            sent_count += 1
        except Exception as e:
            logger.error(f"[SENDNOW] Failed to send post {post.get('id')}: {e}")

    await update.message.reply_text(f"Sent {sent_count} out of {len(posts)} pending posts.")

# ========== ERROR HANDLER ==========
async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)
    if context.error:
        tb_str = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
        logger.error(f"Traceback:\n{tb_str}")
    else:
        logger.error("No exception information available (context.error is None)")

# ========== MAIN FUNCTION FOR CRON MODE ==========
def main():
    """Main function - can run as interactive bot OR as cron job"""
    
    # Check environment variables
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Missing environment variables: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY")
        return

    # Check if running as cron job (environment variable CRON_MODE=true)
    if os.getenv("CRON_MODE", "").lower() == "true":
        logger.info("Running in CRON MODE - sending scheduled posts only")
        import asyncio
        asyncio.run(send_scheduled_posts())
        return

    # Otherwise run as interactive Telegram bot
    logger.info("Running in INTERACTIVE MODE - full bot functionality")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add all command handlers
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
    app.add_handler(CommandHandler("sendnow", sendnow_command))
    app.add_error_handler(error_handler)

    # Add automatic scheduled post checker - runs at specific times daily
    # Times: 9:00 AM, 12:00 PM, 3:00 PM, 6:00 PM, 9:00 PM UK time (UTC+1 currently)
    # Note: Adjust hours by -1 to convert UK time to UTC
    job_queue = app.job_queue
    check_times = [
        time(hour=8, minute=0, tzinfo=timezone.utc),   # 9 AM UK (8 AM UTC)
        time(hour=11, minute=0, tzinfo=timezone.utc),  # 12 PM UK (11 AM UTC)
        time(hour=14, minute=0, tzinfo=timezone.utc),  # 3 PM UK (2 PM UTC)
        time(hour=17, minute=0, tzinfo=timezone.utc),  # 6 PM UK (5 PM UTC)
        time(hour=20, minute=0, tzinfo=timezone.utc),  # 9 PM UK (8 PM UTC)
    ]
    for check_time in check_times:
        job_queue.run_daily(send_scheduled_posts, check_time)
    logger.info("✅ Automatic scheduler enabled - checking at 9AM, 12PM, 3PM, 6PM, 9PM UK time")

    logger.info("Aurion bot starting in interactive mode...")
    app.run_polling()

if __name__ == "__main__":
    main()
