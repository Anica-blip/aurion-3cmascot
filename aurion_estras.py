from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

HASHTAGS = [
    "#Topics",
    "#Blog",
    "#Provisions",
    "#Training",
    "#Knowledge",
    "#Language",
    "#Audiobook",
    "#Healingmusic"
]

TOPICS = [
    {"name": "Aurion Gems", "url": "https://t.me/c/2377255109/138"},
    {"name": "ClubHouse Chatroom", "url": "https://t.me/c/2377255109/10"},
    {"name": "ClubHouse News & Releases", "url": "https://t.me/c/2377255109/6"},
    {"name": "ClubHouse Notices", "url": "https://t.me/c/2377255109/1"},
    {"name": "Weekly Challenges", "url": "https://t.me/c/2377255109/39"},
    {"name": "ClubHouse Mini-Challenges", "url": "https://t.me/c/2377255109/25"},
    {"name": "ClubHouse Learning", "url": "https://t.me/c/2377255109/12"},
    {"name": "3C Evolution Badges", "url": "https://t.me/c/2377255109/355"},
    {"name": "3C LEVEL 1", "url": "https://t.me/c/2377255109/342"},
    {"name": "3C LEVEL 2", "url": "https://t.me/c/2377255109/347"}
]

async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = "Here are the main 3C hashtags:\n" + "\n".join(HASHTAGS)
    await update.message.reply_text(reply + "\n\nFor more information, just ask Aurion!")

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(topic["name"], url=topic["url"])] for topic in TOPICS
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Here are our main 3C folders/topics. Tap to open:",
        reply_markup=reply_markup
    )
