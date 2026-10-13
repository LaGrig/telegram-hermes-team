import os
import sys
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")
draft_path = os.path.join(BASE_DIR, "draft_post.txt")
log_path = os.path.join(BASE_DIR, "editorial.log")

def run_editorial_board():
    print("👔 [Главред] Формирование вечернего дайджеста 17:00 из одобренных тем...")
    if not os.path.exists(catalog_path):
        print("❌ Файл catalog_perks.json не найден.")
        return False

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    selected = []
    # Приоритет: 1 событие, 1 еда, 1 игра/халява, 1 работа
    for cat in ["events", "food", "games", "jobs"]:
        items = catalog.get(cat, [])
        if items:
            selected.append((cat, items[0]))

    if len(selected) < 3:
        print(f"❌ Набрано только {len(selected)} темы. Отмена выпуска.")
        return False

    date_str = datetime.now().strftime("%d.%m")
    total_count = len(selected)
    word_form = "главных предложения" if total_count in [2, 3, 4] else "главных предложений"

    post_lines = [
        f"⚡️ <b>КОШИЦЕ | ВЕЧЕРНИЙ ДАЙДЖЕСТ НА {date_str}</b>\n",
        f"Пары закончились — забираем {total_count} {word_form} вечера:\n"
    ]

    for idx, (cat, it) in enumerate(selected, 1):
        price = it.get("price", "")
        summary = it.get("consumer_reason") or it.get("raw_text", "")
        post_lines.append(f"<b>{idx}. {it.get('title')}</b>")
        post_lines.append(f"💰 <b>Выгода:</b> {price}")
        post_lines.append(f"📌 <b>Оценка студента:</b> {summary}")
        post_lines.append(f"👉 <a href='{it.get('url')}'>Забрать / Источник</a>\n")

    post_lines.append("<i>Полный каталог Кошиц — в приложении ниже ⬇️</i>")
    full_text = "\n".join(post_lines)

    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"✅ [Главред] Черновик сформирован ({total_count} пункта) -> draft_post.txt")
    return True

if __name__ == "__main__":
    success = run_editorial_board()
    sys.exit(0 if success else 1)
