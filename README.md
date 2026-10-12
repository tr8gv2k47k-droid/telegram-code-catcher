# telegram-code-catcher

A Telegram bot that detects and extracts code snippets from plain text and screenshots, saves them in SQLite, and exposes a lightweight dashboard to review recent captures.

## Features

- Detects fenced code blocks such as ```python ... ```
- Detects inline code snippets such as `print("hello")`
- Supports OCR for screenshot uploads via Tesseract
- Stores captured snippets in SQLite
- Includes commands: /start, /help, /extract, /history, /stats
- Exposes a local Flask dashboard for viewing recent snippets
- Docker-ready deployment

## Project structure

- `main.py` – bootstraps the bot and optional dashboard
- `bot.py` – bot logic, code detection, OCR handling, commands
- `db.py` – SQLite functions
- `dashboard.py` – Flask app
- `templates/index.html` – dashboard template
- `requirements.txt` – Python dependencies
- `.env.example` – environment sample
- `.gitignore` – ignored files
- `Dockerfile` – container build
- `docker-compose.yml` – local orchestration

## Local setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

4. Edit `.env` and set your Telegram bot token:

   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   START_WEB_DASHBOARD=true
   WEB_PORT=5000
   ```

5. Start the app:

   ```bash
   python main.py
   ```

6. Open the dashboard in your browser:

   ```text
   http://localhost:5000
   ```

## OCR requirements

To read text from screenshots, install Tesseract OCR:

- macOS:

  ```bash
  brew install tesseract
  ```

- Ubuntu/Debian:

  ```bash
  sudo apt-get install tesseract-ocr
  ```

- Windows:
  Install Tesseract from the official project and add it to PATH.

## Docker

Build and run with Docker:

```bash
docker build -t telegram-code-catcher .
docker run --env-file .env -p 5000:5000 telegram-code-catcher
```

Or with Docker Compose:

```bash
docker-compose up --build
```

## Example usage

Send a message like this:

```python
print("hello from Telegram")
```

The bot will detect the snippet and reply with it.

## License

MIT
