# aurion-3cmascot

A simple Telegram bot connected to OpenAI, ready to deploy on Render, Railway, or similar.

## Features

- `/start` - Welcome message
- `/ask <your question>` - Sends your question to OpenAI and replies with the answer

## Setup

1. **Clone or download all these files into your repository.**
2. **Set the following environment variables in your Render/Railway dashboard:**
    - `TELEGRAM_BOT_TOKEN` — your Telegram bot token from @BotFather
    - `OPENAI_API_KEY` — your OpenAI API key
3. **Deploy as a Background Worker (on Render) or Service (on Railway):**
    - Make sure your `Procfile` is included and set to:  
      `worker: python main.py`
    - The `runtime.txt` ensures Python 3.11 is used.

## Local Testing (optional)

If you want to run locally:
1. Install Python 3.11 if not installed.
2. Run:
    ```
    pip install -r requirements.txt
    export TELEGRAM_BOT_TOKEN=your-telegram-token
    export OPENAI_API_KEY=your-openai-key
    python main.py
    ```
3. Talk to your bot on Telegram!

## License

This project is licensed under the MIT License.