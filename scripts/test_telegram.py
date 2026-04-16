"""Send a one-line test message. Uses .env / env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)."""
from cgd.alerts.telegram import send_telegram_text

if __name__ == "__main__":
    ok = send_telegram_text("CGD: Telegram test — if you see this, alerts are wired.")
    print("sent" if ok else "skipped (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
