import os
import re
import html
import tempfile
from threading import Thread

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot import build_application
from dashboard import create_app
from db import init_db

load_dotenv()


def start_dashboard() -> None:
    if os.getenv("START_WEB_DASHBOARD", "false").lower() != "true":
        return

    app = create_app()
    port = int(os.getenv("WEB_PORT", "5000"))
    thread = Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False),
        daemon=True,
    )
    thread.start()


def main() -> None:
    init_db()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set. Add it to your .env file.")

    start_dashboard()

    application = build_application(bot_token)
    print("Bot started. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
