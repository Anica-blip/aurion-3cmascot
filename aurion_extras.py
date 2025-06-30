from telegram import Update
from telegram.ext import ContextTypes
import re

def extract_hashtags(text):
    """
    Extracts hashtags from the given text.
    Example: "This is a #test" -> ["#test"]
    """
    return re.findall(r"#\w+", text)

def extract_topics(text):
    """
    Dummy function to extract topics from text.
    Replace with your actual logic.
    """
    # Example: split text into words longer than 3 characters
    return [word for word in text.split() if len(word) > 3]

async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Use the utility to show hashtags in the user's message, or default message
    text = update.message.text or ""
    tags = extract_hashtags(text)
    if tags:
        await update.message.reply_text("Found hashtags: " + " ".join(tags))
    else:
        await update.message.reply_text("#3C #Aurion #DigitalCard")

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Use the utility to show topics in the user's message, or default message
    text = update.message.text or ""
    tops = extract_topics(text)
    if tops:
        await update.message.reply_text("Extracted topics: " + ", ".join(tops))
    else:
        await update.message.reply_text("Topics: Digital Identity, Collaboration, Personal Growth")
