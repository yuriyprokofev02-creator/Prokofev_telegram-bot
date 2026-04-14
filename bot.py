import os
import sqlite3
from datetime import datetime, timedelta, timezone

from groq import Groq
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set")

client = Groq(api_key=GROQ_API_KEY)

DB_PATH = "chat_history.db"
HISTORY_TTL_HOURS = 12
MAX_HISTORY_MESSAGES = 20
MAX_MESSAGE_LENGTH = 4000


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cutoff_iso() -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HISTORY_TTL_HOURS)
    return cutoff.isoformat()


def cleanup_old_messages(chat_id: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            "DELETE FROM messages WHERE chat_id = ? AND created_at < ?",
            (chat_id, cutoff_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def save_message(chat_id: str, role: str, content: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO messages (chat_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, role, content, utc_now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def load_recent_history(chat_id: str) -> list[dict[str, str]]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE chat_id = ? AND created_at >= ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, cutoff_iso(), MAX_HISTORY_MESSAGES),
        ).fetchall()

        rows = list(reversed(rows))
        return [{"role": row["role"], "content": row["content"]} for row in rows]
    finally:
        conn.close()


def clear_chat_history(chat_id: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.commit()
    finally:
        conn.close()


def trim_text(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я бот с памятью на 12 часов.\n"
        "Команды:\n"
        "/reset — очистить историю\n"
        "/help — показать помощь"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Я сохраняю историю сообщений в этом чате на 12 часов.\n"
        "Команды:\n"
        "/reset — очистить историю\n"
        "/help — помощь"
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return

    chat_id = str(update.effective_chat.id)
    clear_chat_history(chat_id)
    await update.message.reply_text("История чата очищена.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text or not update.effective_chat:
        return

    chat_id = str(update.effective_chat.id)
    user_text = trim_text(update.message.text.strip())

    cleanup_old_messages(chat_id)
    history = load_recent_history(chat_id)

    messages = [
        {
            "role": "system",
            "content": (
                "Ты полезный, вежливый и понятный ассистент. "
                "Отвечай по-русски. "
                "Учитывай историю текущего чата за последние 12 часов. "
                "Если пользователь просит что-то вспомнить, опирайся только на доступную историю."
            ),
        },
        *history,
        {"role": "user", "content": user_text},
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
        )
        answer = response.choices[0].message.content or "Не получилось сформировать ответ."
        answer = trim_text(answer)
    except Exception:
        answer = "Сервис временно недоступен. Попробуй ещё раз чуть позже."

    save_message(chat_id, "user", user_text)
    save_message(chat_id, "assistant", answer)

    await update.message.reply_text(answer)


def main() -> None:
    init_db()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
