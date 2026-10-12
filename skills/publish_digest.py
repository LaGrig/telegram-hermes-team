import os
import sys
import json
import re
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")
history_path = os.path.join(BASE_DIR, "published_posts.json")
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

def load_history():
    if not os.path.exists(history_path):
        return []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(history):
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def compose_digest():
    if not os.path.exists(catalog_path):
        print("❌ Файл catalog_perks.json не найден.")
        return None

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # Приоритетные рубрики для вечернего дайджеста
    selected_items = []
    priority_order = ["events", "food", "games", "jobs"]

    for cat in priority_order:
        items = catalog.get(cat, [])
        if items:
            selected_items.append(items[0])

    if not selected_items:
        print("⚠️ Нет доступных предложений для дайджеста.")
        return None

    # Форматирование поста
    date_str = datetime.now().strftime("%d.%m")
    lines = [
        f"⚡️ <b>КОШИЦЕ | ВЕЧЕРНИЙ ДАЙДЖЕСТ НА {date_str}</b>\n",
        "Пары закончились — забираем лучшие скидки, раздачи и планы на сегодня:\n"
    ]

    for idx, item in enumerate(selected_items, 1):
        title = item.get("title", "")
        price = item.get("price", "").replace("**", "")
        summary = item.get("summary", "")
        conditions = item.get("conditions", "")
        url = item.get("url", "")

        lines.append(f"<b>{idx}. {title}</b>")
        lines.append(f"💰 <b>Цена/Выгода:</b> {price}")
        lines.append(f"📌 <b>Суть:</b> {summary}")
        if conditions:
            lines.append(f"🪪 <b>Условия:</b> {conditions}")
        lines.append(f"👉 <a href='{url}'>Забрать / Подробнее</a>\n")

    lines.append("<i>Полный каталог верифицированных акций доступен по кнопке ниже ⬇️</i>")
    text = "\n".join(lines)

    # Инлайн-кнопки под постом
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🍔 Еда и ланчи", "callback_data": "cat_food"},
                {"text": "🎮 Игры за 0 €", "callback_data": "cat_games"}
            ],
            [
                {"text": "🎭 Афиша Кошиц", "callback_data": "cat_events"},
                {"text": "💼 Подработки", "callback_data": "cat_jobs"}
            ],
            [
                {"text": "🚀 Открыть весь каталог (Mini App)", "url": "https://t.me"}
            ]
        ]
    }

    return text, reply_markup

def publish_to_telegram():
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or env.get("BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID") or env.get("CHANNEL_ID")

    if not token or not chat_id:
        print("❌ Ошибка: В .env не найдены TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID (CHANNEL_ID).")
        return

    digest = compose_digest()
    if not digest:
        return

    text, reply_markup = digest

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    }

    print(f"📡 Отправляю дайджест в канал {chat_id}...")
    try:
        res = requests.post(url, json=payload, timeout=10)
        res_data = res.json()
        if res_data.get("ok"):
            msg_id = res_data["result"]["message_id"]
            print(f"✅ Дайджест успешно опубликован! Message ID: {msg_id}")
            
            # Сохраняем в историю публикаций для последующего аудита
            history = load_history()
            history.append({
                "message_id": msg_id,
                "chat_id": chat_id,
                "published_at": datetime.now().isoformat()
            })
            save_history(history)
        else:
            print(f"❌ Ошибка Telegram API: {res_data.get('description')}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

if __name__ == "__main__":
    publish_to_telegram()
