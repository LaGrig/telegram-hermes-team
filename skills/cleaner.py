import os
import sys
import json
import time
import datetime
import re
import requests
from skills.use_llm import ask_llm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
history_path = os.path.join(BASE_DIR, "published_posts.json")
manifesto_path = os.path.join(BASE_DIR, "manifesto.md")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("TELEGRAM_CHANNEL_ID", "-1004295999846"))

if not TOKEN:
    print("❌ Ошибка: не задан TELEGRAM_BOT_TOKEN")
    sys.exit(1)

def delete_telegram_post(msg_id):
    url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
    res = requests.post(url, json={"chat_id": CHANNEL_ID, "message_id": msg_id})
    return res.ok or "message to delete not found" in res.text.lower()

mode = sys.argv[1].lower() if len(sys.argv) > 1 else "audit"
now = int(time.time())

# -------------------------------------------------------------
# РЕЖИМ 1: ПРИНУДИТЕЛЬНОЕ УДАЛЕНИЕ ДИАПАЗОНА ID (для постов вне реестра)
# Использование: python skills/cleaner.py scan <последний_id> <сколько_назад>
# Пример: python skills/cleaner.py scan 100 20
# -------------------------------------------------------------
if mode == "scan":
    max_id = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    print(f"🧹 Зачистка канала по диапазону сообщений: от {max_id} назад на {count} постов...")
    deleted = 0
    for m_id in range(max_id, max(0, max_id - count), -1):
        if delete_telegram_post(m_id):
            deleted += 1
            print(f"  ❌ Удалено сообщение #{m_id}")
            time.sleep(0.2)
    print(f"✅ Готово! Удалено из диапазона: {deleted}")
    sys.exit(0)

# Для остальных режимов читаем published_posts.json
if not os.path.exists(history_path):
    print("ℹ️ Реестр published_posts.json пуст.")
    sys.exit(0)

with open(history_path, "r", encoding="utf-8") as f:
    try:
        history = json.load(f)
    except Exception:
        history = []

if not history:
    print("ℹ️ Нет записей об опубликованных постах.")
    sys.exit(0)

deleted_count = 0
manifesto_content = ""
if os.path.exists(manifesto_path):
    with open(manifesto_path, "r", encoding="utf-8") as f:
        manifesto_content = f.read()

# -------------------------------------------------------------
# РЕЖИМ 2: УДАЛИТЬ ВСЕ ИЗ РЕЕСТРА
# -------------------------------------------------------------
if mode in ["all", "everything"]:
    for item in history:
        if item.get("status") != "deleted":
            msg_id = item.get("message_id")
            if delete_telegram_post(msg_id):
                item["status"] = "deleted"
                item["deleted_reason"] = "manual_all"
                deleted_count += 1
                time.sleep(0.3)

# -------------------------------------------------------------
# РЕЖИМ 3: УМНЫЙ АУДИТ (ССЫЛКИ + МАНИФЕСТ + TTL)
# -------------------------------------------------------------
elif mode == "audit":
    print("🧐 Запуск смыслового аудита постов по Манифесту и проверке ссылок...")

    def check_manifesto_compliance(post_text):
        """Проверяет через LLM, соответствует ли пост тематике канала."""
        prompt = f"""Ты — строгий Цензор студенческого Telegram-канала в Кошице.
Манифест канала:
{manifesto_content}

Текст опубликованного поста:
{post_text}

Вопрос: Соответствует ли этот пост теме канала (студенческая жизнь, Кошице/Словакия, экономия, скидки, игры, события до 15€)?
Если пост оффтопный, спамный или вообще не про эту тему — ответь 'НЕТ'.
Если пост нормальный и полезен студентам — ответь 'ДА'.
Ответь ТОЛЬКО одним словом: ДА или НЕТ."""
        try:
            ans = ask_llm(prompt, "Ты цензор.")
            return "ДА" in ans.upper()
        except Exception:
            return True # в случае сбоя сети не удаляем по ошибке

    for item in history:
        if item.get("status") == "deleted":
            continue

        msg_id = item.get("message_id")
        text = item.get("text", "")
        pub_time = item.get("published_at", now)

        # 1. Проверка по Манифесту (смысловой аудит темы)
        is_relevant = check_manifesto_compliance(text)
        if not is_relevant:
            print(f"🚫 Пост #{msg_id} признан ОФФТОПОМ по Манифесту. Удаляю...")
            if delete_telegram_post(msg_id):
                item["status"] = "deleted"
                item["deleted_reason"] = "offtopic_manifesto"
                deleted_count += 1
                time.sleep(0.3)
            continue

        # 2. Проверка по TTL (> 14 дней)
        if (now - pub_time) > (14 * 24 * 3600):
            print(f"⏳ Пост #{msg_id} старше 14 дней. Удаляю...")
            if delete_telegram_post(msg_id):
                item["status"] = "deleted"
                item["deleted_reason"] = "expired_14d"
                deleted_count += 1
                time.sleep(0.3)
            continue

with open(history_path, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

print(f"✅ Аудит завершен. Удалено неактуальных/оффтоп постов: {deleted_count}")
