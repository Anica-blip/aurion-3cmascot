def hashtags(text):
    """
    Extracts hashtags from the given text.
    Example: "This is a #test" -> ["#test"]
    """
    import re
    return re.findall(r"#\w+", text)

def topics(text):
    """
    Dummy function to extract topics from text.
    Replace with your actual logic.
    """
    # Example: split text into words longer than 3 characters
    return [word for word in text.split() if len(word) > 3]
