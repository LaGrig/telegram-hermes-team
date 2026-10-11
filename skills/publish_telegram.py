import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # например: -1001234567890 или @my_channel

def publish_telegram(text: str) -> bool:
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID не заданы")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    resp = requests.post(url, json=payload, timeout=10)
    if resp.ok:
        print("✅ Опубликовано в Telegram")
        return True
    else:
        print(f"❌ Ошибка: {resp.status_code} {resp.text}")
        return False


if __name__ == "__main__":
    # Тест (только если заданы переменные)
    publish_telegram("Тест от Hermes Agent 🚀")
