import os
import sys
import json
import time
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
draft_path = os.path.join(BASE_DIR, "draft_post.txt")
buttons_path = os.path.join(BASE_DIR, "draft_buttons.json")
history_path = os.path.join(BASE_DIR, "published_posts.json")
votes_path = os.path.join(BASE_DIR, "votes.json")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("TELEGRAM_CHANNEL_ID", "-1004295999846"))

if not TOKEN:
    print("❌ Ошибка: не задан TELEGRAM_BOT_TOKEN")
    sys.exit(1)

if not os.path.exists(draft_path):
    print("❌ Ошибка: draft_post.txt не найден")
    sys.exit(1)

with open(draft_path, "r", encoding="utf-8") as f:
    text = f.read().strip()

# Подтягиваем ссылки для кнопок
action_buttons = []
if os.path.exists(buttons_path):
    try:
        with open(buttons_path, "r", encoding="utf-8") as f:
            action_buttons = json.load(f)
    except Exception:
        action_buttons = []

# Формируем клавиатуру:
# Сначала по одной кнопке со ссылкой на каждый пункт
inline_keyboard = []
for btn in action_buttons:
    inline_keyboard.append([{"text": btn["text"], "url": btn["url"]}])

# В самом низу — ряд интерактивных реакций
inline_keyboard.append([
    {"text": "🔥 0", "callback_data": "vote:fire"},
    {"text": "🥱 0", "callback_data": "vote:meh"},
    {"text": "💾 0", "callback_data": "vote:save"}
])

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHANNEL_ID,
    "text": text,
    "parse_mode": "Markdown",
    "reply_markup": {"inline_keyboard": inline_keyboard},
    "disable_web_page_preview": True
}

print("📢 Публикую пост с кнопками ссылок и реакций...")
res = requests.post(url, json=payload)

if not res.ok and "can't parse entities" in res.text:
    payload.pop("parse_mode", None)
    res = requests.post(url, json=payload)

if res.ok:
    data = res.json()
    msg_id = data["result"]["message_id"]
    print(f"🎉 Пост #{msg_id} успешно опубликован в канале!")

    # Запись в историю
    history = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append({
        "message_id": msg_id,
        "published_at": int(time.time()),
        "text": text,
        "status": "published"
    })

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    # Инициализация счетчиков реакций
    votes_db = {}
    if os.path.exists(votes_path):
        try:
            with open(votes_path, "r", encoding="utf-8") as f:
                votes_db = json.load(f)
        except Exception:
            votes_db = {}

    votes_db[str(msg_id)] = {"fire": [], "meh": [], "save": []}
    with open(votes_path, "w", encoding="utf-8") as f:
        json.dump(votes_db, f, ensure_ascii=False, indent=2)
else:
    print(f"❌ Ошибка Telegram API: {res.text}")
    sys.exit(1)
