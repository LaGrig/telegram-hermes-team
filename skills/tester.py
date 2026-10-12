import os
import sys
import json
import re
from skills.use_llm import ask_llm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_json_path = os.path.join(BASE_DIR, "raw_news.json")
filtered_json_path = os.path.join(BASE_DIR, "filtered_news.json")
history_path = os.path.join(BASE_DIR, "published_posts.json")

if not os.path.exists(raw_json_path):
    print("❌ Файл raw_news.json не найден.")
    sys.exit(1)

with open(raw_json_path, "r", encoding="utf-8") as f:
    raw_news = json.load(f)

# Читаем историю
published_context = ""
if os.path.exists(history_path):
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
            recent_texts = [p.get("text", "") for p in history[-8:]]
            published_context = "\n---\n".join(recent_texts)
    except Exception:
        pass

# ЖЕСТКИЙ СТОП-ЛИСТ: дети, старики, и ЛЮБОЙ стандартный транспорт/тарифы
BANNED_WORDS = [
    "dieťa", "deti", "matersk", "škôlk", "dôchod", "senior", "bábät",
    "50%", "50 %", "polovičné", "zľava 50", "cestovné", "mhd", "doprav", 
    "autobus", "zssk", "žsr", "vlaky", "lístok", "lístky"
]

clean_candidates = []
for item in raw_news:
    t_lower = item["title"].lower()
    if not any(bw in t_lower for bw in BANNED_WORDS):
        clean_candidates.append(item)

candidates_text = ""
for item in clean_candidates[:30]:
    candidates_text += f"[ID {item['id']}] [{item.get('category', 'LOCAL')}] {item['title']}\n"

prompt = f"""Ты — циничный студент TUKE/UPJŠ в Кошице с бюджетом 15€.
Никакого транспорта! Никаких детских и официальных отчетов.

УЖЕ ВЫХОДИЛО:
{published_context if published_context else "Пусто"}

КАНДИДАТЫ:
{candidates_text}

ТРЕБОВАНИЯ:
1. Выбери ровно 3 САМЫХ интересных темы (бесплатные фестивали, выставки, ночи музеев, IT-лекции, халява, максимум 1 топовая игра за 0€).
2. Запрещены любые упоминания билетов на транспорт и скидок 50%.
3. Ответь ТОЛЬКО списком из 3 ID через запятую (например: 4, 9, 12)."""

print("🧐 Тестировщик фильтрует новости без транспорта...")
try:
    ans = ask_llm(prompt)
except Exception as e:
    print(f"❌ Ошибка LLM: {e}")
    sys.exit(1)

selected_ids = [int(n) for n in re.findall(r'\b\d+\b', ans)]
selected_news = [item for item in clean_candidates if item["id"] in selected_ids][:3]

if len(selected_news) < 3:
    for item in clean_candidates:
        if item not in selected_news:
            selected_news.append(item)
        if len(selected_news) == 3:
            break

with open(filtered_json_path, "w", encoding="utf-8") as f:
    json.dump(selected_news, f, ensure_ascii=False, indent=2)

print(f"✅ Отобрано {len(selected_news)} тем без транспорта и банальщины.")
