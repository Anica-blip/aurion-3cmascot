import os
import logging
import random
import asyncpg
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from openai import OpenAI

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

client = OpenAI(api_key=OPENAI_API_KEY)

processing_messages = [
    "Hey Champ, give me a second to help you with that!",
    "Hang tight, Champ! Aurion's on it.",
    "One moment, Champ—let me work my magic.",
    "Just a sec, Champ! Let me get that sorted for you.",
]

SIGNOFF = '\n\nOur mission is "We Rise As One", Keep crushing it, Champ! Aurion'

WELCOME = (
    "Hello Champ, Aurion here, the 3C Mascot. Part motivator, part mischief, and now, officially LIVE here on Telegram! "
    "To begin our conversation type /ask <adding your question> so that I can assist you."
)

# --- Database helpers ---
async def get_db_connection():
    return await asyncpg.connect(SUPABASE_DB_URL)

async def has_greeted(user_id):
    conn = await get_db_connection()
    row = await conn.fetchrow('SELECT 1 FROM greeted_users WHERE user_id = $1', user_id)
    await conn.close()
    return row is not None

async def mark_greeted(user_id):
    conn = await get_db_connection()
    # Only insert if not exists
    await conn.execute('INSERT INTO greeted_users (user_id) VALUES ($1) ON CONFLICT DO NOTHING', user_id)
    await conn.close()

# --- Bot commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not await has_greeted(user_id):
        await update.message.reply_text(WELCOME)
        await mark_greeted(user_id)
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
        system_prompt = (
            "You are Aurion, the 3C Mascot: energetic, motivating, a bit cheeky, and always supportive. "
            "Reply in 1-2 short paragraphs. Vary your phrasing for returning users. "
            "After your answer, always add this signoff, separated by a line: "
            "'Our mission is \"We Rise As One\", Keep crushing it, Champ! Aurion'"
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
        if SIGNOFF not in answer:
            answer += SIGNOFF
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text(
            "Sorry Champ, Aurion hit a snag getting your answer.\n"
            f"Error details: {e}\n{SIGNOFF}"
        )

def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not SUPABASE_DB_URL:
        logger.error("One or more environment variables not set (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_DB_URL).")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    print("Aurion is polling. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
