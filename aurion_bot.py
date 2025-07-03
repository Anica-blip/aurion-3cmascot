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
    Example: split text into words longer than 3 characters
    """
    return [word for word in text.split() if len(word) > 3]

# No Telegram handlers here now. All bot command logic is in main.py
