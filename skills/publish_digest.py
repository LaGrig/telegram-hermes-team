import os
import sys
import json
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
draft_path = os.path.join(BASE_DIR, "draft_post.txt")
log_path = os.path.join(BASE_DIR, "editorial.log")
env_path = os.path.join(BASE_DIR, ".env")

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

def publish():
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or env.get("BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID") or env.get("CHANNEL_ID")

    if not token or not chat_id:
        print("❌ Ошибка: В .env нет TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID.")
        return

    if not os.path.exists(draft_path):
        print("❌ Ошибка: draft_post.txt не найден! Главред не утвердил выпуск.")
        return

    with open(draft_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        print("❌ Ошибка: draft_post.txt пуст.")
        return

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🍔 Еда (вечер)", "callback_data": "cat_food"},
                {"text": "🎮 Игры за 0 €", "callback_data": "cat_games"}
            ],
            [
                {"text": "🎭 Афиша Кошиц", "callback_data": "cat_events"},
                {"text": "💼 Подработки", "callback_data": "cat_jobs"}
            ]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    }

    res = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload, timeout=10)
    if res.ok:
        msg_id = res.json()["result"]["message_id"]
        print(f"✅ Утвержденный выпуск опубликован! Message ID: {msg_id}")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [Издатель] Пост опубликован в канал {chat_id} (msg_id={msg_id})\n")
    else:
        print(f"❌ Сбой публикации: {res.text}")

if __name__ == "__main__":
    publish()
