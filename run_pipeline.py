import os
import sys
import subprocess
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
EDITOR_CHAT_ID = os.getenv("TELEGRAM_EDITOR_CHAT_ID")
CANCEL_FLAG = os.path.join(BASE_DIR, "cancel_publish.flag")
DRAFT_PATH = os.path.join(BASE_DIR, "draft_post.txt")

python_bin = sys.executable
env = os.environ.copy()
env["PYTHONPATH"] = BASE_DIR

def notify_editor(text, reply_markup=None):
    if not BOT_TOKEN or not EDITOR_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": EDITOR_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка уведомления Главреда: {e}")

def run_step(step_name, command):
    print(f"\n▶️ [Конвейер] Шаг: {step_name}...")
    res = subprocess.run(command, cwd=BASE_DIR, env=env)
    if res.returncode != 0:
        err_msg = f"🛑 <b>[СТОП]</b> Сбой на шаге «{step_name}». Конвейер остановлен."
        print(err_msg)
        notify_editor(err_msg)
        sys.exit(res.returncode)
    print(f"✅ Шаг '{step_name}' успешно выполнен.")

def prepare_digest():
    # Сбрасываем старый флаг отмены перед новой сборкой
    if os.path.exists(CANCEL_FLAG):
        os.remove(CANCEL_FLAG)

    run_step("1. Сбор сырых данных (Scraper)", [python_bin, "skills/local_scraper.py"])
    run_step("2. Оценка контента и обновление Каталога (LLM QA)", [python_bin, "skills/agent_consumer.py"])
    run_step("3. Редколлегия — верстка дайджеста (Editorial Board)", [python_bin, "skills/editorial.py"])
    run_step("4. Префлайт-контроль ссылок (Quality Gate)", [python_bin, "skills/quality_gate.py"])

    if os.path.exists(DRAFT_PATH):
        with open(DRAFT_PATH, "r", encoding="utf-8") as f:
            draft_text = f.read()

        header = (
            "🕟 <b>ПРЕВЬЮ ДАЙДЖЕСТА (Автопубликация в 17:00)</b>\n"
            "<i>Если всё отлично — ничего делать не нужно, в 17:00 пост уйдет сам.\n"
            "Если нужны правки — просто ответь (Reply) на это сообщение!</i>\n"
            "────────────────────\n\n"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "🚀 Опубликовать прямо сейчас", "callback_data": "publish_digest_now"}],
                [{"text": "🛑 Отменить автопостинг в 17:00", "callback_data": "cancel_autopublish"}]
            ]
        }
        notify_editor(header + draft_text, reply_markup=keyboard)

def publish_only():
    if os.path.exists(CANCEL_FLAG):
        print("⏸ Автопубликация в 17:00 отменена Главредом.")
        notify_editor("⏸ <i>Автопубликация в 17:00 пропущена (была нажата кнопка отмены или пост уже вышел).</i>")
        os.remove(CANCEL_FLAG)
        return

    run_step("5. Публикация в Telegram (Publisher)", [python_bin, "skills/publisher.py"])
    notify_editor("✅ <b>Вечерний дайджест (17:00) автоматически опубликован в основном канале!</b>")

def main():
    print("🚀 Запуск агентного конвейера Hermes Team...")
    if "--publish-only" in sys.argv:
        publish_only()
    elif "--prepare" in sys.argv:
        prepare_digest()
    elif "--publish" in sys.argv:
        prepare_digest()
        publish_only()
    else:
        prepare_digest()

if __name__ == "__main__":
    main()
