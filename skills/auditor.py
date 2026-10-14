import os
import sys
import json
from datetime import datetime
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from skills.llm_worker import ask_llm
from skills.scoring import calculate_perk_score, wave_sort_category

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PUBLIC_CHANNEL_ID = os.getenv("TELEGRAM_CHAT_ID")
EDITOR_CHAT_ID = os.getenv("TELEGRAM_EDITOR_CHAT_ID")

catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")
published_path = os.path.join(BASE_DIR, "published_posts.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StudentAuditor/2.0"}

DEAD_SIGNATURES = [
    "vypredané", "obsadené", "predaj ukončený", "nedostupné",
    "akcia bola ukončená", "udalosť sa skončila", "ponuka je neplatná",
    "registrácia bola ukončená", "kapacita je naplnená",
    "sold out", "expired", "deal ended", "out of stock",
    "no longer available", "registration is closed",
    "out of keys", "all keys claimed", "giveaway has ended", "this giveaway has ended"
]

def check_html_signatures(url, is_evergreen=False):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if res.status_code in [404, 410, 500, 502]:
            return False, f"HTTP {res.status_code}"

        if is_evergreen:
            return True, res.text

        content = res.text.lower()
        for sig in DEAD_SIGNATURES:
            if sig in content:
                return False, f"Найден маркер завершения: '{sig}'"

        return True, res.text
    except Exception as e:
        return False, f"Сбой сети: {str(e)[:50]}"

def mark_shara_expired_in_channel(post: dict):
    """Редактирует пост в основном канале, отмечая 'Ну вот, закончилась..'"""
    msg_id = post.get("message_id")
    chat_id = post.get("chat_id") or PUBLIC_CHANNEL_ID
    title = post.get("title", "Раздача")

    expired_text = (
        f"💨 <b>Ну вот, закончилась..</b>\n\n"
        f"<s>🔥 ШАРА | {title}</s>\n"
        f"<i>Ключи разобрали или акция завершилась. Не выключай звук канала, чтобы успеть на следующую!</i>"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": expired_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"  💨 Пост #{msg_id} ({title}) отмечен как 'Ну вот, закончилась..'")
    except Exception as e:
        print(f"  ⚠️ Не удалось обновить пост #{msg_id}: {e}")

def audit_active_shara():
    """Проверяет все опубликованные посты Шары и зачеркивает сгоревшие."""
    if not os.path.exists(published_path):
        return

    try:
        with open(published_path, "r", encoding="utf-8") as f:
            posts = json.load(f)
        if not isinstance(posts, list):
            return
    except Exception:
        return

    updated = False
    for post in posts:
        if post.get("type") == "shara" and post.get("status") == "active":
            url = post.get("url", "")
            is_alive, reason = check_html_signatures(url)
            if not is_alive:
                mark_shara_expired_in_channel(post)
                post["status"] = "expired"
                post["expired_at"] = datetime.now().isoformat()
                post["expire_reason"] = reason
                updated = True

    if updated:
        with open(published_path, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)

def audit_catalog():
    print("🧹 [Auditor] Запуск проверки активной Шары и каталога Mini App...")
    audit_active_shara()

    if not os.path.exists(catalog_path):
        print("❌ Файл catalog_perks.json не найден.")
        return

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    now = datetime.now()
    stats = {"checked": 0, "deleted": 0, "reasons": []}
    cleaned_catalog = {}

    for cat_name, items in catalog.items():
        survived_items = []
        for item in items:
            stats["checked"] += 1
            item_id = item.get("id", item.get("title", "Без названия"))
            is_evergreen = item.get("urgency") == "evergreen"

            valid_until_str = item.get("valid_until")
            if valid_until_str:
                try:
                    deadline = datetime.fromisoformat(valid_until_str)
                    if now > deadline:
                        stats["deleted"] += 1
                        stats["reasons"].append(f"[{cat_name}] {item_id}: Истёк дедлайн")
                        continue
                except Exception:
                    pass

            url = item.get("url", "")
            if url.startswith("http"):
                is_alive, result_text = check_html_signatures(url, is_evergreen=is_evergreen)
                if not is_alive:
                    stats["deleted"] += 1
                    stats["reasons"].append(f"[{cat_name}] {item_id}: {result_text}")
                    continue

            survived_items.append(item)

        ranked_items = wave_sort_category(survived_items)
        cleaned_catalog[cat_name] = ranked_items

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, ensure_ascii=False, indent=2)

    print(f"\n📊 [Аудит завершен] Проверено: {stats['checked']} | Удалено битых: {stats['deleted']}")

if __name__ == "__main__":
    if "--shara-only" in sys.argv:
        audit_active_shara()
    else:
        audit_catalog()
