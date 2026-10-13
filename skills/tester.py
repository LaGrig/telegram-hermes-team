import os
import sys

# Добавляем корень проекта в sys.path ДО импорта любых skills
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import json
import re
from skills.use_llm import ask_llm

raw_path = os.path.join(BASE_DIR, "raw_news.json")
filtered_path = os.path.join(BASE_DIR, "filtered_news.json")

def test_news():
    print("🧐 [Tester] Начинаю фактчекинг и фильтрацию сырых новостей...")
    if not os.path.exists(raw_path):
        print("❌ Файл raw_news.json не найден.")
        return

    with open(raw_path, "r", encoding="utf-8") as f:
        news_items = json.load(f)

    valid_items = []
    for item in news_items:
        title = item.get("title", "")
        link = item.get("link", "")
        
        # Отсекаем мусорные редиректы Google News
        if "news.google.com" in link:
            continue

        prompt = f"""Ты — въедливый Тестировщик студенческого канала в Кошице.
Новость: "{title}"
Ссылка: "{link}"

Проверь:
1. Имеет ли это отношение к студентам TUKE/UPJŠ или жизни в Кошице?
2. Нет ли здесь явного обмана или неактуального мусора?

Ответь строго JSON: {{"is_valid": true или false, "reason": "почему"}}"""

        try:
            ans = ask_llm(prompt, "Ты беспристрастный QA тестировщик.")
            ans = re.sub(r'```json\s*', '', ans).replace('```', '').strip()
            res = json.loads(ans)
            if res.get("is_valid"):
                valid_items.append(item)
        except Exception:
            valid_items.append(item)

    with open(filtered_path, "w", encoding="utf-8") as f:
        json.dump(valid_items, f, ensure_ascii=False, indent=2)

    print(f"✅ [Tester] Проверено: {len(news_items)} | Одобрено: {len(valid_items)}")

if __name__ == "__main__":
    test_news()
