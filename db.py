import html
import os
import re
import tempfile
from typing import Any, Dict, List

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


def detect_language(text: str) -> str:
    lowered = text.strip().lower()
    if "def " in lowered or "import " in lowered or "print(" in lowered:
        return "python"
    if "function " in lowered or "const " in lowered or "=>" in lowered:
        return "javascript"
    if "class " in lowered and "{\n" in lowered:
        return "java"
    if "<?php" in lowered or "echo " in lowered:
        return "php"
    if "SELECT " in lowered or "INSERT " in lowered:
        return "sql"
    return "text"


def extract_code_snippets(text: str) -> List[Dict[str, str]]:
    snippets: List[Dict[str, str]] = []

    for match in FENCED_CODE_RE.finditer(text):
        language = (match.group("language") or detect_language(match.group("code"))).strip()
        code = match.group("code").strip()
        if code:
            snippets.append({"language": language, "code": code})

    if not snippets:
        for match in INLINE_CODE_RE.finditer(text):
            code = match.group(1).strip()
            if code:
                snippets.append({"language": detect_language(code), "code": code})

    return snippets


def build_response(snippets: List[Dict[str, str]]) -> str:
    parts: List[str] = []
    for index, snippet in enumerate(snippets, start=1):
        language = snippet.get("language") or "text"
        code = html.escape(snippet["code"])
        parts.append(f"<b>Snippet {index} · {language}</b>\n<pre><code>{code}</code></pre>")
    return "\n\n---\n\n".join(parts)


async def save_and_reply(update: Update, snippets: List[Dict[str, str]], source_text: str) -> None:
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
            raw_text=source_text,
        )

    response = build_response(snippets)
    await update.message.reply_text(response, parse_mode=ParseMode.HTML)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I can catch code from messages and screenshots.\n\n"
        "Commands:\n"
        "- /start\n"
        "- /help\n"
        "- /extract\n"
        "- /history\n"
        "- /stats"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Here’s how to use me:\n"
        "- Send code in a regular message\n"
        "- Send a message with fenced code blocks like ```python ... ```\n"
        "- Reply to a message with /extract\n"
        "- Send a screenshot and I’ll try OCR\n"
        "- Use /history and /stats to review saved snippets"
    )


async def extract_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    source_text = ""

    if message.reply_to_message:
        reply = message.reply_to_message
        source_text = reply.text or reply.caption or ""
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
        snippet_preview = (row["code"] or "")[:80].replace("\n", " ")
        lines.append(f"• {row['created_at']} | {row['language'] or 'text'} | {snippet_preview}")

    await update.message.reply_text("\n".join(lines))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = get_stats()
    total = stats.get("total", 0)
    languages = stats.get("languages", {})

    if not languages:
        await update.message.reply_text("No stats yet. Add a snippet and I’ll track it.")
        return

    language_summary = ", ".join(f"{lang}: {count}" for lang, count in languages.items())
    await update.message.reply_text(f"Total snippets: {total}\nLanguage breakdown: {language_summary}")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.effective_message.text or update.effective_message.caption or ""
    if not text or text.startswith("/"):
        return

    snippets = extract_code_snippets(text)
    if not snippets:
        return

    await save_and_reply(update, snippets, text)


def ocr_image_to_text(image_path: str) -> str:
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception:
        return ""


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    file = await photo.get_file()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        await file.download_to_drive(custom_path=temp_path)
        image_text = ocr_image_to_text(temp_path)
        if not image_text:
            await update.message.reply_text("I could not read text from that image. Try uploading a clearer screenshot.")
            return

        snippets = extract_code_snippets(image_text)
        if not snippets:
            await update.message.reply_text("I found text in the image, but no clear code blocks were detected.")
            return

        for snippet in snippets:
            save_snippet(
                user_id=update.effective_user.id,
                username=update.effective_user.username or update.effective_user.first_name,
                chat_id=update.effective_chat.id,
                source="ocr",
                code=snippet["code"],
                language=snippet.get("language") or detect_language(snippet["code"]),
                raw_text=image_text,
            )

        await update.message.reply_text(build_response(snippets), parse_mode=ParseMode.HTML)
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
