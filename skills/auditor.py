import os
import sys
import json
import time
import re
from datetime import datetime
import requests
from skills.use_llm import ask_llm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StudentAuditor/1.2"}

DEAD_SIGNATURES = [
    "vypredané", "obsadené", "predaj ukončený", "nedostupné", 
    "akcia bola ukončená", "udalosť sa skončila", "ponuka je neplatná",
    "registrácia bola ukončená", "kapacita je naplnená",
    "sold out", "expired", "deal ended", "out of stock", 
    "no longer available", "form is no longer accepting responses",
    "registration is closed"
]

def clean_html_content(raw_html):
    text = re.sub(r'<(script|style|nav|footer)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    return ' '.join(text.split())[:1500]

def check_html_signatures(url, is_evergreen=False):
    try:
        res = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if res.status_code in [404, 410, 500, 502]:
            return False, f"HTTP {res.status_code}"

        # Для постоянных сервисов и порталов сигнатуры "распродано" не проверяем
        if is_evergreen:
            return True, res.text

        content = res.text.lower()
        for sig in DEAD_SIGNATURES:
            if sig in content:
                return False, f"Найден маркер завершения: '{sig}'"

        return True, res.text
    except Exception as e:
        return False, f"Сбой сети: {str(e)[:60]}"

def check_via_llm(page_html, title):
    try:
        clean_text = clean_html_content(page_html[:25000])
        current_date_str = datetime.now().strftime("%d.%m.%Y")

        prompt = f"""Ты — аудитор актуальности мероприятий и студенческих скидок.
Текущая дата: {current_date_str}.

Предложение: "{title}"
Фрагмент страницы:
\"\"\"{clean_text}\"\"\"

ВОПРОС: Активно ли это предложение сейчас?
Бракуй ТОЛЬКО если: дата события уже прошла относительно {current_date_str}, регистрация прямо закрыта, мест нет или страница пустая/ошибка.
Ответь строго JSON:
{{"is_active": true или false, "reason": "краткая причина"}}"""

        ans = ask_llm(prompt, "Ты беспристрастный аудитор актуальности.")
        ans = re.sub(r'```json\s*', '', ans).replace('```', '').strip()
        data = json.loads(ans)
        return data.get("is_active", True), data.get("reason", "Одобрено LLM")
    except Exception as e:
        return True, f"LLM пропущена ({e})"

def audit_catalog():
    print("🧹 [Auditor] Запуск тотальной проверки актуальности каталога...")
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

            # УРОВЕНЬ 1: Проверка TTL
            valid_until_str = item.get("valid_until")
            if valid_until_str:
                try:
                    deadline = datetime.fromisoformat(valid_until_str)
                    if now > deadline:
                        stats["deleted"] += 1
                        stats["reasons"].append(f"[{cat_name}] {item_id}: Истёк дедлайн {valid_until_str}")
                        continue
                except Exception:
                    pass

            # УРОВЕНЬ 2: Проверка доступности URL
            url = item.get("url", "")
            if url.startswith("http"):
                is_alive, result_text = check_html_signatures(url, is_evergreen=is_evergreen)
                if not is_alive:
                    stats["deleted"] += 1
                    stats["reasons"].append(f"[{cat_name}] {item_id}: {result_text}")
                    continue

                # УРОВЕНЬ 3: Проверка через LLM (только разовые ивенты)
                if item.get("urgency") in ["limited_slots", "event"]:
                    is_active, llm_reason = check_via_llm(result_text, item.get("title", ""))
                    if not is_active:
                        stats["deleted"] += 1
                        stats["reasons"].append(f"[{cat_name}] {item_id}: Забраковано LLM ({llm_reason})")
                        continue

            survived_items.append(item)

        cleaned_catalog[cat_name] = survived_items[:10]

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, ensure_ascii=False, indent=2)

    print(f"\n📊 [Аудит завершен] Проверено: {stats['checked']} | Удалено неактуальных: {stats['deleted']}")
    for r in stats["reasons"]:
        print(f"  ❌ {r}")

    print("\n📦 [Состояние витрины по рубрикам]:")
    for cat_name, items in cleaned_catalog.items():
        count = len(items)
        status = "🟢 Норма" if count >= 5 else "⚠️ ДЕФИЦИТ (<5)"
        print(f"  • {cat_name.upper():<10}: {count} активных предложений [{status}]")

if __name__ == "__main__":
    audit_catalog()
