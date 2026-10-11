import json
import os
from search_web import search_web_kosice
from publish_telegram import publish_telegram
from use_llm import ask_llm

USERS_FILE = "app/users.json"

def main():
    print("🚀 Запуск конвейера Hermes...")
    if not os.path.exists(USERS_FILE):
        print("❌ База студентов пуста.")
        return

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)

    categories = {}
    for uid, cat in users.items():
        categories.setdefault(cat, []).append(uid)

    for category, user_ids in categories.items():
        print(f"\n🔍 Поиск для {category}...")
        news = search_web_kosice(category, limit=2)
        if not news:
            continue

        raw_data = "\n\n".join([f"Тема: {n['title']}\nСуть: {n['summary']}\nЛинк: {n['link']}" for n in news])
        prompt = "Ты молодежный редактор Telegram-канала для студентов в Кошице. Из этих сырых данных сделай один короткий, сочный пост с эмодзи. Ссылки обязательно оформи через HTML-тег <a>. Язык: русский.\n\n" + raw_data
        
        print("✍️ Писатель (LLM) обрабатывает текст...")
        msg = ask_llm(prompt)

        if msg:
            for uid in user_ids:
                publish_telegram(msg, uid)

if __name__ == "__main__":
    main()
