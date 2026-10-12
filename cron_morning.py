import os
import sys
import subprocess
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = -5457457789

def notify(text):
    if not TOKEN:
        return
    max_len = 4000
    for i in range(0, len(text), max_len):
        chunk = text[i:i + max_len]
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": chunk})

print("🌅 Запуск утреннего конвейера...")
pipeline_path = os.path.join(BASE_DIR, "run_pipeline.py")

result = subprocess.run([sys.executable, pipeline_path], capture_output=True, text=True, cwd=BASE_DIR)

if result.returncode == 0:
    draft_path = os.path.join(BASE_DIR, "draft_post.txt")
    if os.path.exists(draft_path):
        with open(draft_path, "r", encoding="utf-8") as f:
            draft_text = f.read()
        notify(f"🌅 **Доброе утро, Шеф! Свежий дайджест готов:**\n\n{draft_text}\n\n---\n*Жду команду: 'Публикуй' или замечания по правкам.*")
    else:
        notify("⚠️ Утренний конвейер отработал, но draft_post.txt не создан.")
else:
    err_log = result.stderr[-1000:] if result.stderr else result.stdout[-1000:]
    notify(f"🚨 Ошибка утреннего сбора новостей:\n{err_log}")
