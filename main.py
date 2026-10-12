import os
import sys

from dotenv import load_dotenv

from bot import build_application
from dashboard import create_app
from db import init_db

load_dotenv()


def start_dashboard() -> None:
    if os.getenv("START_WEB_DASHBOARD", "false").lower() != "true":
        return

    app = create_app()
    port = int(os.getenv("WEB_PORT", "5000"))
    print(f"Starting web dashboard on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


def main() -> None:
    init_db()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing. Add it to your .env file.")

    app = build_application(token)
    print("Telegram bot started. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot stopped.")
        sys.exit(0)
