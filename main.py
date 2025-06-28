import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import openai

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I'm your AI Telegram bot. Use /ask <your question> to talk to OpenAI."
    )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Please ask a question after /ask")
        return
    user_question = " ".join(context.args)
    await update.message.reply_text("Thinking... 🤔")
    try:
        response = openai.ChatCompletion.create(
    model="gpt-4o-mini",  # Use your available model
    messages=[{"role": "user", "content": user_message}],
    max_tokens=300
)
        answer = response.choices[0].message.content.strip()
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text("Sorry, there was an error getting a response from OpenAI.")

def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        logger.error("TELEGRAM_BOT_TOKEN or OPENAI_API_KEY not set in environment variables.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    print("Bot is polling. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
