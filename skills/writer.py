import os
import sys
import json
import re
from skills.use_llm import ask_llm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
filtered_json_path = os.path.join(BASE_DIR, "filtered_news.json")
draft_path = os.path.join(BASE_DIR, "draft_post.txt")

if not os.path.exists(filtered_json_path):
    print("❌ filtered_news.json не найден")
    sys.exit(1)

with open(filtered_json_path, "r", encoding="utf-8") as f:
    news_items = json.load(f)

if not news_items:
    print("❌ filtered_news.json пуст")
    sys.exit(1)

items_input = []
for it in news_items[:3]:
    items_input.append({
        "id": it["id"],
        "title": it["title"],
        "category": it.get("category", "LOCAL")
    })

prompt = f"""Ты — копирайтер студенческого канала в Кошице.
Оформи ровно 3 отобранные новости строго по структуре карточки.

ВХОДНЫЕ ДАННЫЕ:
{json.dumps(items_input, ensure_ascii=False, indent=2)}

СТРОГИЕ ТРЕБОВАНИЯ:
1. Заполни РЕАЛЬНЫЕ и РАЗНЫЕ данные для каждого пункта.
2. 'price': реальная цена студента (например, '**0 €** (вход свободный)', '**0 €** (вместо 10 €)').
3. 'cta': текст ссылки действия (например: 'Программа и локации', 'Забрать в Steam', 'Регистрация').
4. Никаких шаблонных повторов!

ФОРМАТ ОТВЕТА (ТОЛЬКО ЧИСТЫЙ JSON):
{{
  "main_title": "Дерзкий заголовок дайджеста с эмодзи",
  "items": [
    {{
      "id": {items_input[0]['id']},
      "emoji": "🎭",
      "heading": "Короткий заголовок",
      "price": "**0 €** (вход свободный)",
      "summary": "1-2 емких предложения сути без воды.",
      "conditions": "Реальные условия именно для этого пункта.",
      "cta": "Текст ссылки действия"
    }}
  ]
}}"""

print("✍️ Писатель верстает монолитные карточки...")
raw_reply = ask_llm(prompt, "Ты генерируешь строго валидный JSON.")
raw_reply = re.sub(r'```json\s*', '', raw_reply)
raw_reply = re.sub(r'```\s*', '', raw_reply).strip()

match = re.search(r'\{.*\}', raw_reply, re.DOTALL)
if match:
    data = json.loads(match.group(0))
else:
    print("❌ Ошибка парсинга JSON от модели")
    sys.exit(1)

url_map = {item["id"]: item["url"] for item in news_items}

lines = []
lines.append(f"**{data.get('main_title', '🎓 КОШИЦЕ НА НУЛЯХ')}**\n")

for idx, it in enumerate(data.get("items", [])[:3], 1):
    emoji = it.get("emoji", "📌")
    heading = it.get("heading", "").strip()
    price = it.get("price", "**0 €**").strip()
    summary = it.get("summary", "").strip()
    conditions = it.get("conditions", "").strip()
    cta = it.get("cta", "Подробнее").strip()
    real_url = url_map.get(it.get("id"), "")

    lines.append(f"**{idx}. {emoji} {heading}**")
    lines.append(f"💰 **Цена:** {price}")
    lines.append(f"📌 **Суть:** {summary}")
    lines.append(f"🪪 **Условия:** {conditions}")
    if real_url:
        lines.append(f"👉 [{cta}]({real_url})")
    lines.append("")

final_post = "\n".join(lines).strip()

with open(draft_path, "w", encoding="utf-8") as f:
    f.write(final_post)

print("✅ Черновик с встроенными ссылками готов!")
