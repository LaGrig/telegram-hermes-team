import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def publish_telegram(text: str, chat_id: str) -> bool:
    """Отправляет сообщение конкретному пользователю или в канал"""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан")
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    resp = requests.post(url, json=payload, timeout=10)
    if resp.ok:
        print(f"✅ Успешно отправлено для ID {chat_id}")
        return True
    else:
        print(f"❌ Ошибка отправки: {resp.status_code} {resp.text}")
        return False
