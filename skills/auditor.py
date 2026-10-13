import os
import sys
import json
import time
import re
from datetime import datetime
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from skills.use_llm import ask_llm
from skills.scoring import calculate_perk_score, wave_sort_category

catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StudentAuditor/2.0"}

DEAD_SIGNATURES = [
    "vypredané", "obsadené", "predaj ukončený", "nedostupné", 
    "akcia bola ukončená", "udalosť sa skončila", "ponuka je neplatná",
    "registrácia bola ukončená", "kapacita je naplnená",
    "sold out", "expired", "deal ended", "out of stock", 
    "no longer available", "registration is closed"
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

def audit_catalog():
    print("🧹 [Auditor] Запуск аудита актуальности и скоринга Perk Score...")
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

            # 1. Проверка срока действия
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

            # 2. Проверка ссылки
            url = item.get("url", "")
            if url.startswith("http"):
                is_alive, result_text = check_html_signatures(url, is_evergreen=is_evergreen)
                if not is_alive:
                    stats["deleted"] += 1
                    stats["reasons"].append(f"[{cat_name}] {item_id}: {result_text}")
                    continue

            survived_items.append(item)

        # 3. Скоринг и волновое ранжирование
        ranked_items = wave_sort_category(survived_items)
        cleaned_catalog[cat_name] = ranked_items

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, ensure_ascii=False, indent=2)

    print(f"\n📊 [Аудит завершен] Проверено: {stats['checked']} | Удалено битых: {stats['deleted']}")
    print("\n📦 [Состояние Mini App каталога (ранжированный топ-20)]:")
    for cat_name, items in cleaned_catalog.items():
        count = len(items)
        top_score = items[0].get("perk_score", 0) if items else 0
        status = "🟢 Норма" if count >= 5 else "⚠️ ДЕФИЦИТ"
        print(f"  • {cat_name.upper():<10}: {count:>2} активных предложений (Top Score: {top_score:>2}/100) [{status}]")

if __name__ == "__main__":
    audit_catalog()
