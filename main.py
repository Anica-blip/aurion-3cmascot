import os
import logging
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
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

SIGNOFF = ' Keep crushing it, Champ! Aurion'

WELCOME = (
    "Hello Champ, Aurion here, the 3C Mascot. Part motivator, part mischief, and now, officially LIVE here on Telegram! "
    "To begin our conversation type /ask <adding your question> so that I can assist you."
)

# --- Database helpers using Supabase REST ---
def has_greeted(user_id):
    result = supabase.table("greeted_users").select("user_id").eq("user_id", user_id).execute()
    return len(result.data) > 0

def mark_greeted(user_id):
    supabase.table("greeted_users").insert({"user_id": user_id}).execute()

def get_faq_answer(user_question):
    # Simple keyword match; you can improve this with fuzzy logic later!
    result = supabase.table("faq").select("answer").ilike("question", f"%{user_question}%").execute()
    if len(result.data) > 0:
        return result.data[0]['answer']
    return None

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
        # First, try your FAQ KB
        faq_answer = get_faq_answer(user_question)
        if faq_answer:
            answer = faq_answer.rstrip()
            if not answer.endswith(('.', '!', '?')):
                answer += '.'
            answer = answer + SIGNOFF
        else:
            # Otherwise, use OpenAI
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
            answer = answer.rstrip()
            if not answer.endswith(('.', '!', '?')):
                answer += '.'
            if not answer.endswith(SIGNOFF):
                answer = answer + SIGNOFF
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text(
            f"Sorry Champ, Aurion hit a snag getting your answer. Error details: {e}{SIGNOFF}"
        )

def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("One or more environment variables not set (TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY).")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    print("Aurion is polling. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
