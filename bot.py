import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("8664916218:AAGxtbbVY6aycwhXDrQLVgpKcpuHs6ftrUk")
OPENAI_API_KEY = os.getenv("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")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

client = OpenAI(api_key=OPENAI_API_KEY)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=user_text,
        )
        answer = response.output_text
    except Exception as e:
        answer = f"Ошибка OpenAI: {e}"

    await update.message.reply_text(answer)


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
