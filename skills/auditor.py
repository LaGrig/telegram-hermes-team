import os, sys, json, requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path: sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from skills.scoring import wave_sort_category
from skills.local_scraper import is_dlc_or_pack

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PUBLIC_CHANNEL_ID = os.getenv("TELEGRAM_CHAT_ID")
EDITOR_CHAT_ID = os.getenv("TELEGRAM_EDITOR_CHAT_ID")
catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StudentAuditor/2.0"}

def send_alert_to_admin(text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": EDITOR_CHAT_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: requests.post(url, json=payload, timeout=10)
    except Exception: pass

def check_html_signatures(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if res.status_code in [404, 410, 500, 502]: return False, f"HTTP {res.status_code}"
        return True, "OK"
    except Exception as e:
        return False, f"Сбой: {str(e)[:50]}"

def audit_catalog():
    if not os.path.exists(catalog_path): return
    with open(catalog_path, "r", encoding="utf-8") as f: catalog = json.load(f)

    now, today_str = datetime.now(), datetime.now().strftime("%Y-%m-%d")
    cleaned_catalog = {}

    for cat_name, items in catalog.items():
        survived_items = []
        for item in items:
            item_id = item.get("id", item.get("title", ""))
            
            # Логика для Рекламных (TOP) постов
            if item.get("is_ad"):
                ad_until_str = item.get("ad_until")
                is_expired = False
                if ad_until_str:
                    try:
                        if now > datetime.fromisoformat(ad_until_str): is_expired = True
                    except Exception: pass
                
                url = item.get("url", "")
                is_alive, reason = True, "OK"
                if url.startswith("http"):
                    is_alive, reason = check_html_signatures(url)
                
                if is_expired or not is_alive:
                    if not item.get("alert_sent"):
                        kb = {"inline_keyboard": [[{"text": "Продлить на сутки", "callback_data": f"ad_extend_{item_id}"}, {"text": "Удалить пост", "callback_data": f"ad_delete_{item_id}"}]]}
                        send_alert_to_admin(f"⚠️ <b>Рекламный пост под угрозой!</b>\nПост: {item.get('title')}\nПричина: {'Истек срок размещения' if is_expired else 'Упала ссылка (' + reason + ')'}\nЧто делаем?", reply_markup=kb)
                        item["alert_sent"] = True
                    survived_items.append(item) # Ждем решения админа, не удаляем!
                    continue
                else:
                    item["alert_sent"] = False # Если ссылка ожила, сбрасываем алерт
                    survived_items.append(item)
                    continue

            # Логика для Обычных постов
            if cat_name == "games" and is_dlc_or_pack(item.get("title", ""), item.get("raw_text", "")): continue
            
            valid_until = item.get("valid_until")
            if valid_until:
                try:
                    if now > datetime.fromisoformat(valid_until): continue
                except Exception: pass

            url = item.get("url", "")
            if url.startswith("http"):
                is_alive, _ = check_html_signatures(url)
                if not is_alive: continue

            item["added_date"] = item.get("added_date", today_str)
            item["is_fresh"] = (item["added_date"] == today_str)
            survived_items.append(item)

        cleaned_catalog[cat_name] = wave_sort_category(survived_items)

    with open(catalog_path, "w", encoding="utf-8") as f: json.dump(cleaned_catalog, f, ensure_ascii=False, indent=2)

if __name__ == "__main__": audit_catalog()
