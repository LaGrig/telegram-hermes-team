import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from skills.llm_worker import ask_llm

raw_path = os.path.join(BASE_DIR, "raw_candidates.json")
catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")
cache_path = os.path.join(BASE_DIR, "evaluated_cache.json")

CONSUMER_MANIFESTO = """
ТЫ — ПРЕДСТАВИТЕЛЬ АУДИТОРИИ (Студент 2 курса TUKE/UPJŠ в Кошице).
Твоя цель — эгоистично оценить ценность входящего предложения для студентов.
Отвечай СТРОГО НА РУССКОМ ЯЗЫКЕ.

КРИТЕРИИ ОЦЕНКИ:
1. РАБОТА (jobs):
   - ОДОБРЯЙ: Склад, фасовка, выкладка товаров, бариста, курьер, работа по вечерам/выходным, стажировки без опыта.
   - БРАКУЙ БЕЗ ПОЩАДЫ: Сеньоры, инженеры с дипломом (статисты, конструкторы), менеджеры проектов, полная занятость (8:00–17:00 в будни), сетевой маркетинг (MLM, OVB).

2. ЕДА (food) для вечернего дайджеста (17:00):
   - ОДОБРЯЙ: Вечерние места, пицца, бургеры, бары, скидки по ISIC, работающие после 16:00.
   - БРАКУЙ: Дневные комплексные обеды (закрывающиеся в 14:00-14:30), так как в 17:00 студент на них уже не успеет.

3. ИГРЫ, ХАЛЯВА И СОБЫТИЯ (games/events/shara):
   - ОДОБРЯЙ: Полная халява (0 €), раздачи Steam/Playtest ключей, крупные скидки по ISIC, кинотеатры, тусовки.
   - БРАКУЙ: Мутный спам, микро-скидки (5-10%) на никому не нужный мусор, скучные отчеты деканата.

ФОРМАТ ОТВЕТА (СТРОГО JSON):
{
  "approved": true или false,
  "perk_score": число от 0 до 100,
  "reason": "твой дерзкий, честный вердикт от лица студента на русском языке (1-2 предложения)"
}
"""

def load_cache():
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def evaluate_single_item(item: dict, category: str = "games", use_cache: bool = True) -> dict:
    """Единый фейсконтроль Агента-Потребителя для любой карточки (включая Шару)."""
    cache = load_cache()
    item_id = item.get("id", item.get("url", item.get("title")))

    if use_cache and item_id in cache:
        cached_res = cache[item_id]
        cached_res["from_cache"] = True
        return cached_res

    prompt = (
        f"Категория: {category}\n"
        f"Название: {item.get('title')}\n"
        f"Цена: {item.get('price', '0 €')}\n"
        f"Описание: {item.get('raw_text', '')}"
    )
    decision = ask_llm(CONSUMER_MANIFESTO, prompt, expect_json=True)

    if not decision or "approved" not in decision:
        res = {"approved": False, "perk_score": 0, "reason": "LLM не смогла оценить оффер", "from_cache": False}
    else:
        res = {
            "approved": bool(decision.get("approved", False)),
            "perk_score": int(decision.get("perk_score", 50)),
            "reason": decision.get("reason", ""),
            "from_cache": False
        }

    cache[item_id] = {
        "approved": res["approved"],
        "perk_score": res["perk_score"],
        "reason": res["reason"]
    }
    save_cache(cache)
    return res

def run():
    print("🧠 [Consumer Agent] Запуск ИИ-оценки предложений от лица студента...")
    if not os.path.exists(raw_path):
        print("❌ Файл raw_candidates.json не найден. Сначала запусти скрапер.")
        return

    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    catalog = {cat: [] for cat in raw_data.keys()}
    stats = {"approved": 0, "rejected": 0, "cached": 0}

    for category, items in raw_data.items():
        if category in ["software", "courses", "tourism"]:
            for it in items:
                it["perk_score"] = 80
                it["consumer_reason"] = "Базовый студенческий перк"
                catalog[category].append(it)
            continue

        for it in items:
            res = evaluate_single_item(it, category, use_cache=True)
            if res.get("from_cache"):
                stats["cached"] += 1

            if res.get("approved"):
                stats["approved"] += 1
                it["perk_score"] = res.get("perk_score", 70)
                it["consumer_reason"] = res.get("reason", "")
                catalog[category].append(it)
                if not res.get("from_cache"):
                    print(f"  🟢 [ОДОБРЕНО] [{category}] {it.get('title')[:40]} | Score: {it['perk_score']}")
                    print(f"     💬 Вердикт: {it['consumer_reason']}")
            else:
                stats["rejected"] += 1
                if not res.get("from_cache"):
                    print(f"  🔴 [ОТКЛОНЕНО] [{category}] {it.get('title')[:40]}")
                    print(f"     💬 Причина: {res.get('reason')}")

    for cat in catalog:
        catalog[cat].sort(key=lambda x: x.get("perk_score", 0), reverse=True)

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n📊 [Итоги оценки] Одобрено: {stats['approved']} | Отклонено: {stats['rejected']} (Из кэша: {stats['cached']})")
    print("✅ База catalog_perks.json успешно обновлена проверенными офферами.")

if __name__ == "__main__":
    run()
