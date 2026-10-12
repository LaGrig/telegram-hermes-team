import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates").json()

found = False
for item in resp.get("result", []):
    chat = item.get("message", {}).get("chat", {})
    if chat.get("type") in ["group", "supergroup"]:
        print(f"✅ Найден чат '{chat.get('title')}'. Его ID: {chat.get('id')}")
        found = True
        break

if not found:
    print("❌ Группа не найдена. Убедись, что добавил бота в группу и написал туда сообщение!")
