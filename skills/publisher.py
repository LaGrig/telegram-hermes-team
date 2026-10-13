import os
import sys
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, ".env")
draft_path = os.path.join(BASE_DIR, "draft_post.txt")

def load_env():
    env = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env()
BOT_TOKEN = env.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = env.get("TELEGRAM_CHAT_ID")
# Ссылка на Mini App (по умолчанию ставим заглушку, можно переопределить в .env)
MINI_APP_URL = env.get("MINI_APP_URL", "https://t.me/HermesKosiceBot/app")

def publish_to_telegram():
    print("📤 [Publisher] Подготовка к отправке дайджеста в Telegram...")
    
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не найдены в .env")
        return False

    if not os.path.exists(draft_path):
        print("❌ ОШИБКА: Файл draft_post.txt не найден!")
        return False

    with open(draft_path, "r", encoding="utf-8") as f:
        text = f.read()

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Добавляем Inline-кнопку
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📱 Открыть полный каталог", "url": MINI_APP_URL}]
        ]
    }

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,  # Отключаем "простыни" превьюшек от ссылок
        "reply_markup": reply_markup
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        print("✅ [Publisher] УСПЕХ! Дайджест опубликован в канале.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ ОШИБКА при отправке в Telegram: {e}")
        if e.response is not None:
            print(f"Ответ API: {e.response.text}")
        return False

if __name__ == "__main__":
    success = publish_to_telegram()
    sys.exit(0 if success else 1)
