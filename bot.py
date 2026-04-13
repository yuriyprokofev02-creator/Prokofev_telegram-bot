from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import openai

openai.api_key = "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"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_text}]
    )

    reply = response['choices'][0]['message']['content']
    await update.message.reply_text(reply)

app = ApplicationBuilder().token("8664916218:AAGxtbbVY6aycwhXDrQLVgpKcpuHs6ftrUk").build()
app.add_handler(MessageHandler(filters.TEXT, handle))

print("Бот запущен...")
app.run_polling()