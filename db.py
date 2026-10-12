import sqlite3
from typing import Dict, List

DB_PATH = "code_snippets.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                chat_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                language TEXT,
                code TEXT NOT NULL,
                raw_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def save_snippet(
    user_id: int,
    username: str,
    chat_id: int,
    source: str,
    code: str,
    language: str,
    raw_text: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO snippets (user_id, username, chat_id, source, language, code, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, chat_id, source, language, code, raw_text),
        )
        connection.commit()


def fetch_recent(limit: int = 10) -> List[Dict[str, str]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, username, chat_id, source, language, code, raw_text, created_at
            FROM snippets
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_stats() -> Dict[str, object]:
    with get_connection() as connection:
        total_result = connection.execute("SELECT COUNT(*) as count FROM snippets").fetchone()
        total = total_result["count"] if total_result else 0

        language_rows = connection.execute(
            """
            SELECT language, COUNT(*) as count
            FROM snippets
            GROUP BY language
            ORDER BY count DESC
            """
        ).fetchall()

        languages = {row["language"] or "text": row["count"] for row in language_rows}
        return {"total": total, "languages": languages}
