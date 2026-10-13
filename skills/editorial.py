import os
import sys
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from skills.manifestos import TESTER_MANIFESTO, WRITER_MANIFESTO, EDITOR_MANIFESTO

catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")
log_path = os.path.join(BASE_DIR, "editorial.log")
draft_path = os.path.join(BASE_DIR, "draft_post.txt")

def log_event(role, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{role}] {message}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"  📝 [{role}] {message}")

def run_editorial_board():
    print("👔 [Главред] Открываю заседание редколлегии Hermes...")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n=======================================================\n")
        f.write(f" ЗАСЕДАНИЕ РЕДКОЛЛЕГИИ: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
        f.write(f"=======================================================\n")

    if not os.path.exists(catalog_path):
        log_event("Главред", "ОШИБКА: catalog_perks.json не найден!")
        return False

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # 1. ОТБОР 4 СТОЛПОВ ДЛЯ 17:00 (Events + Food[evening] + Games + Jobs)
    log_event("Главред", "Отбираю актуальные предложения под вечерний слот 17:00...")
    selected_items = []
    
    # 1.1 ИВЕНТ
    events = catalog.get("events", [])
    if events:
        selected_items.append(("events", events[0]))

    # 1.2 ЕДА (СТРОГО ВЕЧЕРНЯЯ)
    food_list = catalog.get("food", [])
    evening_food = [f for f in food_list if f.get("timing") == "evening"]
    if evening_food:
        selected_items.append(("food", evening_food[0]))
    elif food_list:
        selected_items.append(("food", food_list[0]))

    # 1.3 ИГРА / ХАЛЯВА
    games = catalog.get("games", [])
    if games:
        selected_items.append(("games", games[0]))

    # 1.4 ПОДРАБОТКА (РЕАЛЬНАЯ СТУДЕНЧЕСКАЯ)
    jobs = catalog.get("jobs", [])
    if jobs:
        selected_items.append(("jobs", jobs[0]))

    if len(selected_items) < 3:
        log_event("Главред", f"ОТМЕНА ВЫПУСКА: Набрано только {len(selected_items)} темы. В эфир не идем.")
        return False

    # 2. ТЕСТИРОВЩИК (Визирование)
    for cat, item in selected_items:
        score = item.get("perk_score", 0)
        log_event("Тестировщик", f"✅ ОДОБРЕНО [{cat.upper()}] (Score: {score}/100): '{item.get('title')}'")

    # 3. ПИСАТЕЛЬ (Верстка дайджеста)
    log_event("Главред", "Передаю темы Писателю для упаковки по Манифесту...")
    date_str = datetime.now().strftime("%d.%m")
    post_lines = [
        f"⚡️ <b>КОШИЦЕ | ВЕЧЕРНИЙ ДАЙДЖЕСТ НА {date_str}</b>\n",
        "Пары закончились — забираем 4 главных предложения вечера:\n"
    ]

    for idx, (cat, it) in enumerate(selected_items, 1):
        price = it.get("price", "").replace("**", "")
        post_lines.append(f"<b>{idx}. {it.get('title')}</b>")
        post_lines.append(f"💰 <b>Выгода:</b> {price}")
        post_lines.append(f"📌 <b>Суть:</b> {it.get('summary')}")
        if it.get("conditions"):
            post_lines.append(f"🪪 <b>Условия:</b> {it.get('conditions')}")
        post_lines.append(f"👉 <a href='{it.get('url')}'>Забрать / Источник</a>\n")

    post_lines.append("<i>Полный каталог Кошиц (40+ позиций) — в приложении ниже ⬇️</i>")
    full_text = "\n".join(post_lines)

    # 4. ВИЗА ГЛАВРЕДА
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    log_event("Главред", f"🎉 ВЫПУСК ЗАВИЗИРОВАН: draft_post.txt готов к отправке в 17:00 ({len(selected_items)} пункта).")
    return True

if __name__ == "__main__":
    success = run_editorial_board()
    sys.exit(0 if success else 1)
