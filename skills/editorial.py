import os
import time
import requests
import subprocess
from skills.use_llm import ask_llm

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = -5457457789

def send_message(text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text})

def listen():
    print(f"🎧 Редакция запущена. Слушаю чат {CHAT_ID}...")
    send_message("👋 Редакция Hermes снова в строю! Я выучил карту проекта.")
    offset = 0
    while True:
        try:
            updates = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": offset, "timeout": 30}).json()
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                
                if msg.get("chat", {}).get("id") == CHAT_ID:
                    text = msg.get("text", "")
                    if text.lower().startswith("dev_bot"):
                        send_message("👨‍💻 Принял задачу. Изучаю карту проекта и пишу код...")
                        
                        # Читаем карту проекта из файла
                        project_map = ""
                        if os.path.exists("skills/readme.txt"):
                            with open("skills/readme.txt", "r", encoding="utf-8") as f:
                                project_map = f.read()

                        # Формируем умный промпт
                        prompt = f'''Ты dev_bot. Пользователь просит: "{text}". 
Твоя задача — написать Python-скрипт, который выполнит эту задачу, используя функцию dev_autofix("описание", "путь_к_файлу", "новое_содержимое").
Формат ответа: ТОЛЬКО рабочий Python код. Никаких пояснений, никаких markdown (без ```python).
В начале обязательно: from skills.dev_autofix import dev_autofix

ОБЯЗАТЕЛЬНАЯ КАРТА ПРОЕКТА ДЛЯ ПОИСКА ФАЙЛОВ:
{project_map}'''
                        
                        script_code = ask_llm(prompt, "Ты генератор Python кода.")
                        script_code = script_code.replace("```python", "").replace("```", "").strip()
                        
                        with open("temp_task.py", "w", encoding="utf-8") as f:
                            f.write(script_code)
                        
                        send_message("⚙️ Запускаю написанный код...")
                        
                        result = subprocess.run(["python", "temp_task.py"], capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            send_message(f"✅ Успех! Код отправлен на GitHub.\n\nЛог:\n{result.stdout[-300:]}")
                        else:
                            send_message(f"❌ Ошибка в написанном коде:\n{result.stderr[-300:]}")
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    listen()
