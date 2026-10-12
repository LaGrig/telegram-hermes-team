import os
import sys
import time
import json
import requests
import subprocess
import traceback
from skills.use_llm import ask_llm

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = -5457457789

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not BASE_DIR or BASE_DIR == "/":
    BASE_DIR = os.getcwd()

votes_path = os.path.join(BASE_DIR, "votes.json")
history_chat_path = os.path.join(BASE_DIR, "chat_history.json")

def send_message(text):
    max_len = 4000
    for i in range(0, len(text), max_len):
        chunk = text[i:i + max_len]
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": chunk,
            "disable_web_page_preview": True
        })

def answer_callback(cb_id, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id, "text": text})

def handle_vote(cb):
    cb_id = cb["id"]
    user_id = cb["from"]["id"]
    msg = cb.get("message")
    if not msg:
        answer_callback(cb_id, "Ошибка")
        return

    chat_id = msg["chat"]["id"]
    msg_id = str(msg["message_id"])
    data = cb.get("data", "")
    if not data.startswith("vote:"):
        return

    action = data.split(":")[1]
    votes_db = {}
    if os.path.exists(votes_path):
        try:
            with open(votes_path, "r", encoding="utf-8") as f:
                votes_db = json.load(f)
        except Exception:
            votes_db = {}

    if msg_id not in votes_db:
        votes_db[msg_id] = {"fire": [], "meh": [], "save": []}

    post_votes = votes_db[msg_id]
    user_list = post_votes.get(action, [])

    if user_id in user_list:
        user_list.remove(user_id)
        toast = "Голос отозван"
    else:
        for act in ["fire", "meh", "save"]:
            if user_id in post_votes.get(act, []):
                post_votes[act].remove(user_id)
        user_list.append(user_id)
        toast = {"fire": "Огонь! 🔥", "meh": "Мимо 🥱", "save": "В закладках! 💾"}.get(action, "Голос учтён!")

    post_votes[action] = user_list
    votes_db[msg_id] = post_votes
    with open(votes_path, "w", encoding="utf-8") as f:
        json.dump(votes_db, f, ensure_ascii=False, indent=2)

    fire_c = len(post_votes.get("fire", []))
    meh_c = len(post_votes.get("meh", []))
    save_c = len(post_votes.get("save", []))

    new_kb = {
        "inline_keyboard": [
            [
                {"text": f"🔥 {fire_c}", "callback_data": "vote:fire"},
                {"text": f"🥱 {meh_c}", "callback_data": "vote:meh"},
                {"text": f"💾 {save_c}", "callback_data": "vote:save"}
            ]
        ]
    }

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/editMessageReplyMarkup",
        json={"chat_id": chat_id, "message_id": int(msg_id), "reply_markup": new_kb}
    )
    answer_callback(cb_id, toast)

def get_editorial_context():
    """Собирает полное актуальное состояние редакции для умного ответа."""
    manifesto = ""
    draft = ""
    filtered = []
    
    man_path = os.path.join(BASE_DIR, "manifesto.md")
    draft_path = os.path.join(BASE_DIR, "draft_post.txt")
    fil_path = os.path.join(BASE_DIR, "filtered_news.json")

    if os.path.exists(man_path):
        manifesto = open(man_path, "r", encoding="utf-8").read()
    if os.path.exists(draft_path):
        draft = open(draft_path, "r", encoding="utf-8").read()
    if os.path.exists(fil_path):
        try:
            filtered = json.load(open(fil_path, "r", encoding="utf-8"))
        except Exception:
            pass

    return f"""=== МАНИФЕСТ РЕДАКЦИИ ===
{manifesto}

=== ТЕКУЩИЙ ЧЕРНОВИК ВЫПУСКА ===
{draft if draft else "Черновик пуст"}

=== ОТОБРАННЫЕ ТЕСТИРОВЩИКОМ ТЕМЫ (filtered_news.json) ===
{json.dumps(filtered, ensure_ascii=False, indent=2)}"""

def listen():
    print(f"🎧 Умный Главред на связи. Слушаю чат {CHAT_ID}...")
    send_message("💼 Главред на связи. Полный доступ к редакции, манифесту и фильтрам активирован.")
    offset = 0

    while True:
        try:
            updates = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": offset, "timeout": 30}).json()
            for update in updates.get("result", []):
                offset = update["update_id"] + 1

                if "callback_query" in update:
                    handle_vote(update["callback_query"])
                    continue

                msg = update.get("message", {})
                if msg.get("chat", {}).get("id") == CHAT_ID:
                    text = msg.get("text", "")
                    if not text:
                        continue
                    text_lower = text.lower().strip()
                    cleaner_path = os.path.join(BASE_DIR, "skills", "cleaner.py")
                    pub_path = os.path.join(BASE_DIR, "skills", "publisher.py")

                    # ПУБЛИКАЦИЯ
                    if any(word in text_lower for word in ["публикуй", "опубликуй", "выкладывай"]):
                        send_message("📢 Публикую дайджест в канал...")
                        res = subprocess.run([sys.executable, pub_path], capture_output=True, text=True, cwd=BASE_DIR)
                        send_message(f"🎉 Результат:\n{res.stdout.strip()}")
                        continue

                    # СБОР ДАЙДЖЕСТА С НУЛЯ
                    if any(word in text_lower for word in ["собери дайджест", "собери пост", "новый дайджест", "запусти конвейер"]):
                        send_message("🚀 Главред: Запускаю конвейер с жестким ситом...")
                        pipeline_path = os.path.join(BASE_DIR, "run_pipeline.py")
                        res = subprocess.run([sys.executable, pipeline_path], capture_output=True, text=True, cwd=BASE_DIR)
                        draft_path = os.path.join(BASE_DIR, "draft_post.txt")
                        draft_txt = open(draft_path, "r", encoding="utf-8").read() if os.path.exists(draft_path) else "Пусто"
                        send_message(f"📰 **Дайджест собран:**\n\n{draft_txt}\n\n---\n*Шеф, жду отмашки: 'Публикуй' или разбираем замечания.*")
                        continue

                    # УДАЛЕНИЕ / ЧИСТКА
                    if any(k in text_lower for k in ["удали все", "очисти канал"]):
                        res = subprocess.run([sys.executable, cleaner_path, "all"], capture_output=True, text=True, cwd=BASE_DIR)
                        send_message(f"🗑️ Результат:\n{res.stdout.strip()}")
                        continue

                    # УМНЫЙ ДИАЛОГ С ШЕФОМ
                    # Главред анализирует вопрос, видит файлы, манифест и историю
                    context_data = get_editorial_context()
                    
                    dialog_prompt = f"""Ты — Главный Редактор студенческого медиа в Кошице.
Твой собеседник — Издатель и Владелец канала (Шеф).
Ты лично отвечаешь головой за качество каждого поста, за отбор тем и за работу своих агентов (Тестировщика, Сборщика, Писателя).

КОНТЕКСТ РЕДАКЦИИ ПРЯМО СЕЙЧАС:
{context_data}

СООБЩЕНИЕ ОТ ШЕФА:
"{text}"

ТВОИ ПРАВИЛА:
1. Отвечай честно, профессионально, по-деловому, без пустой вежливости.
2. Если Шеф указывает на ошибку (например, почему попала скидка 50% или почему кнопки оторваны) — проанализируй данные, четко объясни причину бага/выбора, признай косяк и скажи, ЧТО ты конкретно сделал или готов сделать прямо сейчас (например: "Пересобираю без этой новости").
3. Если Шеф требует убрать тему или изменить черновик — предложи конкретное решение или скажи, что запускаешь пересборку."""

                    ans = ask_llm(dialog_prompt, "Ты профессиональный Главред, строгий к себе и подчиненным.")
                    send_message(ans)

        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    listen()
