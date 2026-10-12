# telegram-code-catcher

A Telegram bot that detects and extracts code snippets from messages and replies with the code in a readable format.

## Features

- Detects fenced code blocks like ```python ... ```
- Detects inline code snippets like `print("hello")`
- Supports `/start` and `/help`
- Supports `/extract` to pull code from a message or reply
- Easy to run locally or deploy to a server

## Project structure

- `main.py` – bot logic
- `requirements.txt` – dependencies
- `.gitignore` – ignored files
- `.env.example` – example environment configuration

## Local setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment file and add your Telegram token:
   ```bash
   cp .env.example .env
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

## Telegram bot configuration

Create a bot with BotFather and copy the token into `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Example usage

Send any message containing code like:

```python
print("hello from Telegram")
```

The bot will detect it and respond with the extracted code.

## License

MIT
