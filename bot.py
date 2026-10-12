import html
import os
import re
import tempfile
from typing import Dict, List

import pytesseract
from PIL import Image
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from db import fetch_recent, get_stats, save_snippet

FENCED_CODE_RE = re.compile(
    r"```(?P<language>[A-Za-z0-9_+-]+)?\s*(?P<code>.*?)\s*```",
    re.DOTALL,
)
INLINE_CODE_RE = re.compile(r"`([^`\n]{3,})`")


def detect_language(code: str) -> str:
    value = code.strip().lower()
    if not value:
        return "text"
    if "import " in value or "def " in value or "print(" in value or "if __name__" in value:
        return "python"
    if "function " in value or "const " in value or "=>" in value or "console.log" in value:
        return "javascript"
    if "SELECT " in value or "INSERT " in value or "CREATE TABLE" in value:
        return "sql"
    if "<?php" in value or "echo " in value or "function " in value and "$" in value:
        return "php"
    if "#include" in value or "int main" in value or "printf(" in value:
        return "c"
    if "curl " in value or "apt-get " in value or "sudo " in value:
        return "bash"
    return "text"


def extract_code_snippets(text: str) -> List[Dict[str, str]]:
    snippets: List[Dict[str, str]] = []

    for match in FENCED_CODE_RE.finditer(text):
        code = match.group("code").strip()
        if not code:
            continue
        lang = (match.group("language") or detect_language(code)).strip()
        snippets.append({"language": lang, "code": code})

    if snippets:
        return snippets

    for match in INLINE_CODE_RE.finditer(text):
        code = match.group(1).strip()
        if not code:
            continue
        snippets.append({"language": detect_language(code), "code": code})

    return snippets


def build_response(snippets: List[Dict[str, str]]) -> str:
    parts: List[str] = []
    for index, snippet in enumerate(snippets, start=1):
        language = snippet.get("language") or "text"
        code = html.escape(snippet["code"])
        parts.append(f"<b>Snippet {index} • {language}</b>\n<pre><code>{code}</code></pre>")
    return "\n\n---\n\n".join(parts)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I can capture code from messages and screenshots.\n\n"
        "Commands:\n"
        "- /start\n"
        "- /help\n"
        "- /extract\n"
        "- /history\n"
        "- /stats"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "How to use me:\n"
        "- Send a text message with code snippets\n"
        "- Send fenced code blocks like ```python ... ```\n"
        "- Reply to a message with /extract\n"
        "- Upload a screenshot and I will try OCR\n"
        "- Use /history or /stats to review saved snippets"
    )


async def extract_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return

    source_text = ""
    if message.reply_to_message:
        source_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    else:
        source_text = message.text or ""

    source_text = source_text.replace("/extract", "").strip()
    snippets = extract_code_snippets(source_text)

    if not snippets:
        await message.reply_text("No code snippets found in that message.")
        return

    for snippet in snippets:
        save_snippet(
            user_id=update.effective_user.id,
            username=update.effective_user.username or update.effective_user.first_name,
            chat_id=update.effective_chat.id,
            source="command",
            code=snippet["code"],
            language=snippet.get("language") or detect_language(snippet["code"]),
            raw_text=source_text,
        )

    await message.reply_text(build_response(snippets), parse_mode=ParseMode.HTML)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    recent = fetch_recent(limit=5)
    if not recent:
        await update.message.reply_text("No saved snippets yet.")
        return

    lines = []
    for row in recent:
        preview = (row["code"] or "")[:80].replace("\n", " ")
        lines.append(f"• {row['created_at']} | {row['language'] or 'text'} | {preview}")

    await update.message.reply_text("\n".join(lines))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = get_stats()
    total = stats.get("total", 0)
    language_summary = stats.get("languages", {})

    if not language_summary:
        await update.message.reply_text("No stats yet. Once you save a snippet, I’ll track it here.")
        return

    summary = ", ".join(f"{lang}: {count}" for lang, count in language_summary.items())
    await update.message.reply_text(f"Total snippets: {total}\nLanguage breakdown: {summary}")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return

    text = message.text or message.caption or ""
    if not text or text.startswith("/"):
        return

    snippets = extract_code_snippets(text)
    if not snippets:
        return

    for snippet in snippets:
        save_snippet(
            user_id=update.effective_user.id,
            username=update.effective_user.username or update.effective_user.first_name,
            chat_id=update.effective_chat.id,
            source="text",
            code=snippet["code"],
            language=snippet.get("language") or detect_language(snippet["code"]),
            raw_text=text,
        )

    await message.reply_text(build_response(snippets), parse_mode=ParseMode.HTML)


def ocr_image_to_text(image_path: str) -> str:
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception:
        return ""


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.photo:
        return

    photo = message.photo[-1]
    file = await photo.get_file()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        await file.download_to_drive(custom_path=temp_path)
        extracted = ocr_image_to_text(temp_path)
        if not extracted:
            await message.reply_text("I could not read any text from that image. Try a clearer screenshot.")
            return

        snippets = extract_code_snippets(extracted)
        if not snippets:
            await message.reply_text("I found text, but no clear code snippets were detected.")
            return

        for snippet in snippets:
            save_snippet(
                user_id=update.effective_user.id,
                username=update.effective_user.username or update.effective_user.first_name,
                chat_id=update.effective_chat.id,
                source="ocr",
                code=snippet["code"],
                language=snippet.get("language") or detect_language(snippet["code"]),
                raw_text=extracted,
            )

        await message.reply_text(build_response(snippets), parse_mode=ParseMode.HTML)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def build_application(bot_token: str) -> Application:
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("extract", extract_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return application
