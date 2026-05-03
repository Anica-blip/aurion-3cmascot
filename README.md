# aurion-3cmascot

This project is part of the 3C Thread To Success™ ecosystem — a growing digital platform that combines creativity, structure, and real-world application.

The 3C Thread To Success™ brand, including its name, structure, characters (Aurion 3C Mascot), and overall system design, remains the intellectual property of the creator and is not included in this license.

Commercial use of the brand or replication of the ecosystem identity is not permitted without permission.

---

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

---

## 🎨 Credits

*Designed and Built by GitHub Copilot × Chef Anica · 3C Thread To Success™ Cooking Lab*  🧪👨‍🍳

---

## 👤 Creator

Anica-blip (“Chef”)
Founder of 3C Thread To Success™ ("Cooking Lab")
Independent Creator | Community Builder

---

🧠 Philosophy

“Think it. Do it. Own it.”

This project was built from vision, persistence, and a commitment to creating meaningful and structured experiences — even with minimal resources.
