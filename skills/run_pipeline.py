import json
import os
from search_web import search_web_kosice
from publish_telegram import publish_telegram

USERS_FILE = "app/users.json"

def main():
    print("🚀 Запуск конвейера Hermes...")
    
    if not os.path.exists(USERS_FILE):
        print(f"❌ Файл {USERS_FILE} не найден. Никто еще не выбрал категории.")
        return

    # 1. Читаем базу пользователей
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)

    # 2. Группируем пользователей по интересам
    # Результат: {'Еда и промокоды': ['123456789', '987654321']}
    categories = {}
    for user_id, category in users.items():
        categories.setdefault(category, []).append(user_id)

    # 3. Ищем новости и делаем рассылку
    for category, user_ids in categories.items():
        print(f"\n🔍 Поиск для категории: {category} (подписчиков: {len(user_ids)})")
        
        # Ищем 2 самые свежие акции/новости
        news = search_web_kosice(category, limit=2)
        if not news:
            print("Ничего не найдено.")
            continue

        # Формируем сообщение
        msg = f"🔥 <b>Свежее по твоей теме: {category}</b>\n\n"
        for item in news:
            summary = item['summary'][:150] + "..." if len(item['summary']) > 150 else item['summary']
            msg += f"🔸 <b>{item['title']}</b>\n{summary}\n<a href='{item['link']}'>Читать далее</a>\n\n"

        # 4. Отправляем сообщение каждому студенту из этой группы
        for uid in user_ids:
            publish_telegram(msg, uid)

if __name__ == "__main__":
    main()
