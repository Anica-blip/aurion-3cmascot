import os
import logging
import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
)
from openai import OpenAI
from supabase import create_client, Client
from aurion_extras import send_due_messages_job  # unchanged, but must be sync!

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

# --- Database helpers using Supabase REST ---
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

# --- /faq command ---
def faq(update: Update, context):
    try:
        data = supabase.table("faq").select("id,question").execute()
        faqs = data.data or []
        if not faqs:
            update.message.reply_text(
                "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
            return
        keyboard = [
            [InlineKeyboardButton(q["question"], callback_data=f'faq_{q["id"]}')] for q in faqs
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Select a FAQ:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Supabase FAQ error: {e}")
        update.message.reply_text(
            "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

def faq_button(update: Update, context):
    try:
        query = update.callback_query
        query.answer()
        faq_id = query.data.replace('faq_', '')
        data = supabase.table("faq").select("answer").eq("id", faq_id).single().execute()
        answer = data.data['answer'] if data.data else "No answer found."
        query.edit_message_text(answer)
    except Exception as e:
        logger.error(f"Supabase FAQ button error: {e}")
        update.callback_query.edit_message_text(
            "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

# --- /fact command ---
def fact(update: Update, context):
    try:
        data = supabase.table("fact").select("fact").execute()
        facts = [item['fact'] for item in data.data] if data.data else []
        if facts:
            update.message.reply_text(f"💎 Aurion Fact:\n{random.choice(facts)}")
        else:
            update.message.reply_text(
                "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
    except Exception as e:
        logger.error(f"Supabase fact error: {e}")
        update.message.reply_text(
            "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

# --- /resources command ---
def resources(update: Update, context):
    try:
        data = supabase.table("resources").select("title,link").execute()
        resources_list = data.data or []
        if not resources_list:
            update.message.reply_text(
                "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
            )
            return
        msg_lines = [f"[{item['title']}]({item['link']})" for item in resources_list]
        update.message.reply_text("Here are some resources:\n" + "\n".join(msg_lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Supabase resources error: {e}")
        update.message.reply_text(
            "Sorry, Champ! Aurion can’t fetch this right now due to technical issues. Try again later, or contact an admin if this continues."
        )

# --- /rules command ---
def rules(update: Update, context):
    update.message.reply_text(f"Community Rules: {RULES_LINK}")

# --- Welcome new members ---
def welcome_new_member(update: Update, context):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        update.message.reply_text(WELCOME)

# --- Farewell members ---
def farewell_member(update: Update, context):
    left_member = update.message.left_chat_member
    if not left_member.is_bot:
        update.message.reply_text(FAREWELL)

# --- Keyword-based replies ---
KEYWORD_RESPONSES = [
    ("help", "If you need a hand, just type /ask followed by your question! Aurion's got your back."),
    ("motivate", "You’re stronger than you think, Champ! Every step counts."),
    ("thanks", "Anytime, Champ! Let’s keep that good energy rolling!"),
    # Add more as you wish
]

def keyword_responder(update: Update, context):
    text = update.message.text.lower()
    for keyword, response in KEYWORD_RESPONSES:
        if keyword in text:
            update.message.reply_text(response)
            break

# --- Bot commands ---
def start(update: Update, context):
    user_id = update.effective_user.id
    if not has_greeted(user_id):
        update.message.reply_text(WELCOME)
        mark_greeted(user_id)
    else:
        update.message.reply_text(
            random.choice(processing_messages)
        )

def ask(update: Update, context):
    user_id = update.effective_user.id
    if not context.args:
        update.message.reply_text("Champ, you gotta ask a question after /ask!")
        return
    user_question = " ".join(context.args)
    update.message.reply_text(random.choice(processing_messages))
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
        update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        update.message.reply_text(
            ensure_signoff_once(f"Sorry Champ, Aurion hit a snag getting your answer. Error details: {e}", SIGNOFF)
        )

# --- /id card command ---
def id_command(update: Update, context):
    update.message.reply_text("Check out our digital 3C /id card: https://anica-blip.github.io/3c-links/")

# --- /help command with 'guidance' reference and resources mention ---
def help_command(update: Update, context):
    update.message.reply_text(
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

# --- /topics command with custom list ---
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

def topics(update: Update, context):
    update.message.reply_text("Please press this /topics and the list below should be the response after pressing /topics")
    msg_lines = []
    for idx, (title, url) in enumerate(TOPICS_LIST, 1):
        msg_lines.append(f"{idx}) [{title}]({url})")
    msg = "\n".join(msg_lines)
    update.message.reply_text(msg, parse_mode="Markdown")

# --- /hashtags command with custom list ---
HASHTAGS_LIST = [
    "#Topics",
    "#Blog",
    "#Provisions",
    "#Training",
    "#Knowledge",
    "#Language",
    "#Audiobook",
    "#Healingmusic",
]

def hashtags(update: Update, context):
    update.message.reply_text("Please press this /hashtags and the list below should be the response after pressing /hashtags")
    msg = "\n".join(HASHTAGS_LIST)
    update.message.reply_text(msg)

# --- Scheduled job for v13 (must be sync!) ---
def scheduled_job(context):
    send_due_messages_job(context, supabase)

def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("One or more environment variables not set (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY).")
        return

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ask", ask))
    dp.add_handler(CommandHandler("faq", faq))
    dp.add_handler(CallbackQueryHandler(faq_button, pattern="^faq_"))
    dp.add_handler(CommandHandler("fact", fact))
    dp.add_handler(CommandHandler("resources", resources))
    dp.add_handler(CommandHandler("rules", rules))
    dp.add_handler(CommandHandler("id", id_command))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("hashtags", hashtags))
    dp.add_handler(CommandHandler("topics", topics))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome_new_member))
    dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, farewell_member))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, keyword_responder))

    # --- Schedule the Supabase job to run every 60 seconds ---
    updater.job_queue.run_repeating(scheduled_job, interval=60, first=10)

    print("Aurion is polling. Press Ctrl+C to stop.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
    print("Aurion is polling. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
