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

3. ИГРЫ И СОБЫТИЯ (games/events):
   - ОДОБРЯЙ: Халява (0 €), реальные скидки по ISIC, кинотеатры, тусовки.
   - БРАКУЙ: Официальные скучные отчеты, научные заседания деканата.

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

def run():
    print("🧠 [Consumer Agent] Запуск ИИ-оценки предложений от лица студента...")
    if not os.path.exists(raw_path):
        print("❌ Файл raw_candidates.json не найден. Сначала запусти скрапер.")
        return

    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    cache = load_cache()
    catalog = {cat: [] for cat in raw_data.keys()}
    stats = {"approved": 0, "rejected": 0, "cached": 0}

    for category, items in raw_data.items():
        # Статические рубрики (софт, курсы, туризм) одобряются автоматически
        if category in ["software", "courses", "tourism"]:
            for it in items:
                it["perk_score"] = 80
                it["consumer_reason"] = "Базовый студенческий перк"
                catalog[category].append(it)
            continue

        for it in items:
            item_id = it["id"]
            
            # Проверяем кэш
            if item_id in cache:
                cached_res = cache[item_id]
                stats["cached"] += 1
                if cached_res.get("approved"):
                    it["perk_score"] = cached_res.get("perk_score", 70)
                    it["consumer_reason"] = cached_res.get("reason", "")
                    catalog[category].append(it)
                    stats["approved"] += 1
                else:
                    stats["rejected"] += 1
                continue

            # Отправляем в LLM
            prompt = f"Категория: {category}\nНазвание: {it.get('title')}\nЦена: {it.get('price')}\nОписание: {it.get('raw_text')}"
            decision = ask_llm(CONSUMER_MANIFESTO, prompt, expect_json=True)

            if not decision or "approved" not in decision:
                # Фоллбэк, если LLM не ответила
                approved = False
                reason = "LLM не смогла оценить оффер"
                score = 0
            else:
                approved = decision.get("approved", False)
                reason = decision.get("reason", "")
                score = decision.get("perk_score", 50)

            # Сохраняем в кэш
            cache[item_id] = {
                "approved": approved,
                "perk_score": score,
                "reason": reason
            }

            if approved:
                stats["approved"] += 1
                it["perk_score"] = score
                it["consumer_reason"] = reason
                catalog[category].append(it)
                print(f"  🟢 [ОДОБРЕНО] [{category}] {it.get('title')[:40]} | Score: {score}")
                print(f"     💬 Вердикт: {reason}")
            else:
                stats["rejected"] += 1
                print(f"  🔴 [ОТКЛОНЕНО] [{category}] {it.get('title')[:40]}")
                print(f"     💬 Причина: {reason}")

    save_cache(cache)

    # Сортируем одобренные офферы по Perk Score
    for cat in catalog:
        catalog[cat].sort(key=lambda x: x.get("perk_score", 0), reverse=True)

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\n📊 [Итоги оценки] Одобрено: {stats['approved']} | Отклонено: {stats['rejected']} (Из кэша: {stats['cached']})")
    print(f"✅ База catalog_perks.json успешно обновлена проверенными офферами.")

if __name__ == "__main__":
    run()
