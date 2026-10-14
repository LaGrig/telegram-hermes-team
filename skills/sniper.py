import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from skills.agent_consumer import evaluate_single_item
from skills.auditor import check_html_signatures

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PUBLIC_CHANNEL_ID = os.getenv("TELEGRAM_CHAT_ID")
EDITOR_CHAT_ID = os.getenv("TELEGRAM_EDITOR_CHAT_ID")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://t.me/HermesKosiceBot/app")

PUBLISHED_FILE = os.path.join(BASE_DIR, "published_posts.json")
CATALOG_FILE = os.path.join(BASE_DIR, "catalog_perks.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HermesSniper/1.0"}

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        try:
            with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_published(data):
    with open(PUBLISHED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_to_catalog(item):
    if not os.path.exists(CATALOG_FILE):
        return
    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        if isinstance(catalog, dict):
            cat = "games" if "games" in catalog else list(catalog.keys())[0]
            catalog.setdefault(cat, []).insert(0, item)
            with open(CATALOG_FILE, "w", encoding="utf-8") as f:
                json.dump(catalog, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Ошибка записи Шары в каталог: {e}")

def publish_shara_to_channel(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": PUBLIC_CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {
            "inline_keyboard": [[{"text": "📱 Открыть полный каталог", "url": MINI_APP_URL}]]
        }
    }
    res = requests.post(url, json=payload, timeout=10)
    res.raise_for_status()
    return res.json()["result"]["message_id"]

def notify_editor(text: str):
    if not EDITOR_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        json={"chat_id": EDITOR_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10
    )

def run_sniper(force_check: bool = False) -> str:
    print("🎯 [Sniper] Сканирование горящих раздач (ШАРА)...")
    api_url = "https://www.gamerpower.com/api/giveaways?platform=pc"
    try:
        res = requests.get(api_url, headers=HEADERS, timeout=12)
        res.raise_for_status()
        games = res.json()
    except Exception as e:
        return f"❌ Ошибка сети Снайпера: {e}"

    published = load_published()
    published_ids = {p.get("item_id") for p in published if isinstance(p, dict)}

    urgent_keywords = ["keys", "beta", "playtest", "limited", "steam", "free", "giveaway"]

    for g in games[:12]:
        item_id = f"shara_{g.get('id')}"
        if item_id in published_ids and not force_check:
            continue

        title = g.get("title", "")
        instructions = g.get("instructions", "")
        platforms = g.get("platforms", "")
        worth = g.get("worth", "0 €")
        if worth in ["N/A", "", None]:
            worth = "Платно"
        link = g.get("open_giveaway_url") or g.get("open_giveaway")

        # Пропускаем обычные недельные раздачи Epic Games (они для вечернего дайджеста)
        if "epic games" in platforms.lower() and "keys" not in title.lower():
            continue

        if not any(kw in (title + " " + instructions + " " + platforms).lower() for kw in urgent_keywords):
            continue

        print(f"🔍 Проверяю кандидата: {title}...")

        # 1. Проверка живости ссылки
        is_alive, dead_reason = check_html_signatures(link)
        if not is_alive:
            print(f"  ⏭ Ссылка мертва ({dead_reason}), пропускаю.")
            continue

        # 2. Фейсконтроль через нашего Агента-Потребителя!
        candidate = {
            "id": item_id,
            "title": title,
            "price": f"0 € (вместо {worth})",
            "url": link,
            "raw_text": f"Платформа: {platforms}. Описание: {g.get('description', '')} Инструкция: {instructions}"
        }
        verdict = evaluate_single_item(candidate, category="games", use_cache=not force_check)
        score = verdict.get("perk_score", 0)
        reason = verdict.get("reason", "")

        print(f"  🧠 Вердикт Потребителя: Approved={verdict.get('approved')} | Score={score} | {reason}")

        if verdict.get("approved") and score >= 65:
            post_text = (
                f"🔥 <b>ШАРА | {title}</b>\n\n"
                f"💰 <b>Выгода:</b> <s>{worth}</s> → <b>0 €</b>\n"
                f"📌 <b>Оценка студента:</b> {reason}\n"
                f"⏳ <b>Статус:</b> Активно (количество ограничено)\n"
                f"👉 <a href='{link}'>Забрать / Источник</a>"
            )

            # Мгновенная автопубликация в канал без ожидания подтверждения!
            msg_id = publish_shara_to_channel(post_text)

            # Сохраняем ID сообщения и ссылку для проверки актуальности
            published.append({
                "type": "shara",
                "item_id": item_id,
                "message_id": msg_id,
                "chat_id": PUBLIC_CHANNEL_ID,
                "title": title,
                "url": link,
                "original_text": post_text,
                "status": "active",
                "published_at": datetime.now().isoformat()
            })
            save_published(published)

            # Сразу добавляем в каталог Mini App
            candidate["perk_score"] = score
            candidate["consumer_reason"] = reason
            add_to_catalog(candidate)

            report = (
                f"🎯 <b>Снайпер автоматически опубликовал ШАРУ в канал!</b>\n"
                f"<i>Прошло фильтр Потребителя (Score: {score}/100)</i>\n"
                f"────────────────────\n\n{post_text}"
            )
            notify_editor(report)
            return report

    return "🔭 Снайпер проверил эфир: новых горящих раздач, прошедших фильтр Потребителя, сейчас нет."

if __name__ == "__main__":
    print(run_sniper())
