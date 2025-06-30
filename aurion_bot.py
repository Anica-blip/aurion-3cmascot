import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ChatMemberHandler
from supabase import create_client, Client

# --- ENV VARIABLES ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789")) # Replace with your Telegram user ID

# --- SUPABASE CLIENT ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- STATIC DATA ---
HASHTAGS = [
    "#Topics", "#Blog", "#Provisions", "#Training", "#Knowledge",
    "#Language", "#Audiobook", "#Healingmusic"
]
TOPICS = [
    "Aurion Gems", "ClubHouse Chatroom", "ClubHouse News & Releases",
    "ClubHouse Notices", "Weekly Challenges", "ClubHouse Mini-Challenges",
    "ClubHouse Learning", "3C LEVEL 1", "3C LEVEL 2"
]
RULES_LINK = "https://t.me/c/2377255109/6/400"
GITHUB_LINK = "https://anica-blip.github.io/3c-links/"

WELCOME_MSG = (
    "Welcome to 3C Thread To Success –your ultimate space for personal transformation and growth. "
    "Whether you're dreaming big or taking small steps, we’re here to help you think it, do it, and own it!\n\n"
    "You've just joined a vibrant community built to turn your life into a purpose-driven adventure —filled with clarity, confidence, and courage. 🌱\n\n"
    "💎 Here’s something we believe in deeply:\n"
    "Every person is a diamond —even if you're still buried in the rough. Growth isn’t about becoming someone else... "
    "it’s about polishing what’s already there. So take your time, trust the process, and shine brighter with every step.\n\n"
    "For everything you need, head over to:\n👉 {github_link}\n"
    "There you’ll find our success links, tools, goal setting, challenges, and more. Or just send me a message —I’m Aurion, your guide along this journey.\n\n"
    "Together, we rise. Together, we polish. Together, we shine. 💫\n"
    "Let’s embark on this adventure and make a difference —one gem at a time."
)
FAREWELL_MSG = (
    "Sad to see you go. Remember, you’re always welcome back. "
    "Stay strong and focused on polishing your diamond. 💎🔥"
)

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name or "there"
    await update.message.reply_text(f"Hey, Champ {first_name}! Aurion at your service. Use /help to see what I can do.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ Aurion Command List:\n"
        "/faq - Browse FAQ\n"
        "/hashtags - Show hashtags\n"
        "/topics - Show topic list\n"
        "/rules - View community rules\n"
        "/fact - Get a random fact\n"
        "/manual_post <message> - (Owner only) Post as Aurion\n"
        "/id - Get the 3C Links web app\n"
        "Ask me anything or use keywords for quick help! 💬"
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Community Rules: {RULES_LINK}")

async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hashtags:\n" + "\n".join(HASHTAGS))

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Topics:\n" + "\n".join(TOPICS))

async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = supabase.table("fact").select("fact").execute()
    facts = [item['fact'] for item in data.data] if data.data else []
    if facts:
        import random
        await update.message.reply_text(f"💎 Aurion Fact:\n{random.choice(facts)}")
    else:
        await update.message.reply_text("No facts found in the database.")

async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fetch FAQ from Supabase, show as InlineKeyboard
    data = supabase.table("faq").select("id,question,answer").execute()
    faqs = data.data or []
    if not faqs:
        await update.message.reply_text("No FAQ available yet.")
        return
    keyboard = [
        [InlineKeyboardButton(q["question"], callback_data=f'faq_{q["id"]}')] for q in faqs
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a FAQ:", reply_markup=reply_markup)

async def faq_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    faq_id = query.data.replace('faq_', '')
    data = supabase.table("faq").select("answer").eq("id", faq_id).single().execute()
    answer = data.data['answer'] if data.data else "No answer found."
    await query.edit_message_text(answer)

async def manual_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Only the owner can send manual posts.")
        return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /manual_post <message>")
        return
    await update.message.reply_text(f"📢 {msg}")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Check out our web app: {GITHUB_LINK}")

async def echo_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Checks all keywords in DB, replies if message contains one.
    text = update.message.text.lower()
    data = supabase.table("keyword").select("keyword,response").execute()
    for item in data.data or []:
        if item["keyword"].lower() in text:
            await update.message.reply_text(item["response"])
            return

async def schedule_messages(context: ContextTypes.DEFAULT_TYPE):
    # This function can be scheduled using JobQueue for actual scheduling
    data = supabase.table("message").select("*").execute()
    for item in data.data or []:
        content = item["content"]
        group_channel = item["group_channel"]
        # For now, just sends to a hardcoded chat/channel (expand as needed)
        await context.bot.send_message(chat_id=group_channel, text=content)

# --- WELCOME/FAREWELL EVENTS ---

async def greet_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_member.new_chat_member.user
    if not user.is_bot:
        await context.bot.send_message(
            chat_id=update.chat_member.chat.id,
            text=WELCOME_MSG.format(github_link=GITHUB_LINK)
        )

async def farewell_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_member.old_chat_member.user
    if not user.is_bot:
        await context.bot.send_message(
            chat_id=update.chat_member.chat.id,
            text=FAREWELL_MSG
        )

# --- MAIN ---

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("hashtags", hashtags))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("fact", fact))
    app.add_handler(CommandHandler("faq", faq))
    app.add_handler(CommandHandler("manual_post", manual_post))
    app.add_handler(CommandHandler("id", id_command))  # <-- Added handler for /id
    app.add_handler(CallbackQueryHandler(faq_button, pattern="^faq_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_keyword))

    # Greet/farewell on join/leave (for groups)
    app.add_handler(ChatMemberHandler(greet_user, ChatMemberHandler.CHAT_MEMBER))
    # To use farewell, you might need custom logic depending on group settings.

    # You can schedule messages using app.job_queue.run_repeating(schedule_messages, interval=86400, first=0)
    # Fill in actual scheduling logic as needed.

    app.run_polling()

if __name__ == "__main__":
    main()
