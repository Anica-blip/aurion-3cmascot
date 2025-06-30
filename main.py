import logging
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import openai

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

openai.api_key = OPENAI_API_KEY

processing_messages = [
    "Hold tight Champ, Aurion is working on it…",
    "Give me a sec, I’m thinking…",
    "Cooking up an answer for you…",
    "Just a moment, making sure you get the best response…"
]

# Handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey Champ! I’m Aurion, your 3C assistant. Type /ask followed by your question and I’ll help you out!"
    )

# Handler for /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Type /ask followed by your question to get an answer. Try /id to see your digital 3C /id card!"
    )

# Handler for /id with updated wording
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Check out our digital 3C /id card: https://anica-blip.github.io/3c-links/")

# Handler for /ask
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Champ, you gotta ask a question after /ask!")
        return
    user_question = " ".join(context.args)
    await update.message.reply_text(random.choice(processing_messages))
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Aurion, the 3C assistant."},
                {"role": "user", "content": user_question},
            ],
            max_tokens=256,
            temperature=0.7
        )
        answer = completion["choices"][0]["message"]["content"]
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        await update.message.reply_text("Oops! Something went wrong. Please try again later.")

# Handler for /faq and buttons (if present in your bot)
async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("What is 3C?", callback_data="faq_what_is_3c")],
        [InlineKeyboardButton("How do I use Aurion?", callback_data="faq_how_to_use")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a question:", reply_markup=reply_markup)

async def faq_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "faq_what_is_3c":
        await query.edit_message_text("3C stands for Connect, Communicate, Collaborate.")
    elif query.data == "faq_how_to_use":
        await query.edit_message_text("Just type /ask followed by your question!")

# Handler for /hashtags and /topics (if present)
async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("#3C #Aurion #DigitalCard")

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Topics: Digital Identity, Collaboration, Personal Growth")

# Welcome and farewell handlers (if present)
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"Welcome {member.full_name}! I’m Aurion, your 3C assistant. Type /ask followed by your question!"
        )

async def farewell_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    left_member = update.message.left_chat_member
    await update.message.reply_text(f"Goodbye {left_member.full_name}! We’ll miss you.")

# Keyword responder for simple keywords (if present)
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
            return

def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("One or more environment variables not set (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY).")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("faq", faq))
    app.add_handler(CallbackQueryHandler(faq_button, pattern="^faq_"))
    app.add_handler(CommandHandler("hashtags", hashtags))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, farewell_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, keyword_responder))
    print("Aurion is polling. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
