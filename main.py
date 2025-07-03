import os
import logging
import random
import re
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

def ensure_signoff_once(answer, signoff):
    pattern = r'[\s.]*' + re.escape(signoff) + r'[\s.]*$'
    answer = re.sub(pattern, '', answer.strip())
    if not answer.endswith(('.', '!', '?')):
        answer += '.'
    return answer + ' ' + signoff

# --- Database helpers using Supabase REST ---
def has_greeted(user_id):
    result = supabase.table("greeted_users").select("user_id").eq("user_id", user_id).execute()
    return len(result.data) > 0

def mark_greeted(user_id):
    supabase.table("greeted_users").insert({"user_id": user_id}).execute()

def get_faq_answer(user_question):
    result = supabase.table("faq").select("answer").ilike("question", f"%{user_question}%").execute()
    if len(result.data) > 0:
        return result.data[0]['answer']
    return None

# ------------------- FAQ BUTTON HANDLER --------------------
FAQ_QUESTIONS = [
    "What is the 3C Thread To Success ecosystem?",
    "Who is Aurion?",
    "Who is Caelum?",
    "What kind of experience can I expect here?",
]

async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = []
    for question in FAQ_QUESTIONS:
        data = supabase.table("faq").select("id,question").eq("question", question).single().execute()
        if data.data:
            buttons.append([InlineKeyboardButton(question, callback_data=f'faq_{data.data["id"]}')])
    if not buttons:
        await update.message.reply_text("No FAQ available yet.")
        return
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose a question:", reply_markup=reply_markup)

async def faq_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    faq_id = query.data.replace('faq_', '')
    data = supabase.table("faq").select("answer").eq("id", faq_id).single().execute()
    answer = data.data['answer'] if data.data else "No answer found."
    await query.edit_message_text(answer)

# --- Welcome new members ---
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        await update.message.reply_text(WELCOME)

# --- Farewell members ---
async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    left_member = update.message.left_chat_member
    if not left_member.is_bot:
        await update.message.reply_text(FAREWELL)

# --- Keyword-based replies ---
KEYWORD_RESPONSES = [
    ("help", "If you need a hand, just type /ask followed by your question! Aurion's got your back."),
    ("motivate", "You’re stronger than you think, Champ! Every step counts."),
    ("thanks", "Anytime, Champ! Let’s keep that good energy rolling!"),
    # Add more as you wish
]

async def keyword_responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    for keyword, response in KEYWORD_RESPONSES:
        if keyword in text:
            await update.message.reply_text(response)
            break

# --- Bot commands ---
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

# --- /id card command ---
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Check out our digital 3C /id card: https://anica-blip.github.io/3c-links/")

# --- /help command with 'guidance' reference ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let me know exactly what you're looking for so that I can guide you.\n\n"
        "You can ask Aurion for tips, facts, or guidance. Try /faq, /hashtags, /topics, /id, or type your question!"
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

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Instructions message
    await update.message.reply_text("Please press this /topics and the list below should be the response after pressing /topics")

    # Build the message with titles and links
    msg_lines = []
    for idx, (title, url) in enumerate(TOPICS_LIST, 1):
        msg_lines.append(f"{idx}) [{title}]({url})")
    msg = "\n".join(msg_lines)
    await update.message.reply_text(msg, parse_mode="Markdown")

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

async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Instructions message
    await update.message.reply_text("Please press this /hashtags and the list below should be the response after pressing /hashtags")

    # Build the message with hashtags
    msg = "\n".join(HASHTAGS_LIST)
    await update.message.reply_text(msg)

def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("One or more environment variables not set (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY).")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("faq", faq))
    app.add_handler(CallbackQueryHandler(faq_button, pattern="^faq_"))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("hashtags", hashtags))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, keyword_responder))
    print("Aurion is polling. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
