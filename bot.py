import os

print("DEBUG TELEGRAM_TOKEN exists:", bool(os.getenv("TELEGRAM_TOKEN")))
print("DEBUG OPENAI_API_KEY exists:", bool(os.getenv("OPENAI_API_KEY")))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    print("ENV KEYS:", sorted(list(os.environ.keys())))
    raise RuntimeError("TELEGRAM_TOKEN is not set")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")
