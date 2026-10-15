import os, re, sys, json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path: sys.path.insert(0, BASE_DIR)
from skills.llm_worker import ask_llm

raw_path = os.path.join(BASE_DIR, "raw_candidates.json")
catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")
rejected_path = os.path.join(BASE_DIR, "rejected_log.json")

CONSUMER_MANIFESTO = """ТЫ — СТУДЕНТ 2 КУРСА TUKE В КОШИЦЕ И РЕДАКТОР КАНАЛА.
Твоя задача — отобрать только лучшее для студентов, перевести на русский и написать суть.

ЖЕСТКИЕ ПРАВИЛА ОТБОРА:
1. РАБОТА (jobs): ОДОБРЯЙ только почасовые подработки (brigáda, na dohodu). БРАКУЙ работу с окладом в месяц, SBS/охрану, фулл-тайм.
2. ЕДА И СОБЫТИЯ (food, events): ОДОБРЯЙ скидки по ISIC, вечерние заведения (Tabačka, Kino Úsmev), кино, выставки.
3. ИГРЫ (games): ОДОБРЯЙ полные бесплатные игры. БРАКУЙ DLC, Starter Pack.
4. КУРСЫ (courses):
   - ОДОБРЯЙ: IT (Python, QA, Data Science, SQL), AI, иностранные языки (особенно словацкий/английский), дизайн (Figma, Adobe), маркетинг, Excel, продуктивность.
   - БРАКУЙ БЕЗЖАЛОСТНО: Инфоцыганство, крипто-трейдинг, ставки, астрологию, эзотерику, таро, курсы MBA для директоров, дачный ландшафт, устаревшие технологии.
   - ОДОБРЯЙ только если скидка 100%, либо курс изначально бесплатен (включая режим Audit).

ПРАВИЛА ТЕКСТА:
- Переведи словацкие слова. НЕ ПЕРЕВОДИ названия брендов (Subway, Coursera, Udemy), улиц (Gorkého) и локаций (Kulturpark).
- В поле "reason" напиши 1-2 живых предложения о сути курса/предложения. НЕ дублируй цену.

ОЦЕНКА (perk_score 0-100):
- Полностью бесплатные курсы (Coursera, edX) или 100% купон Udemy: 85-95 баллов.
- Одобренная Еда и Ивенты: 75-85 баллов.

ФОРМАТ ОТВЕТА (СТРОГО JSON): 
{"approved": true/false, "perk_score": 85, "title_ru": "Заголовок", "reason": "Суть без воды"}"""

def evaluate_single_item(item: dict, cat: str) -> dict:
    if item.get("urgency") == "evergreen" or cat in ["software", "tourism"]:
        return {"approved": True, "perk_score": 88, "title_ru": item.get("title"), "reason": item.get("raw_text")}
    
    prompt = f"Категория: {cat}\nЗаголовок: {item.get('title')}\nЦена: {item.get('price', '')}\nОписание: {item.get('raw_text')}"
    decision = ask_llm(CONSUMER_MANIFESTO, prompt, expect_json=True)
    
    if decision and "approved" in decision:
        score = decision.get("perk_score", 70)
        if cat == "courses" and decision.get("approved"): score = max(score, 80) 
        return {
            "approved": decision.get("approved"),
            "perk_score": score,
            "title_ru": decision.get("title_ru") or item.get("title"),
            "reason": decision.get("reason") or item.get("raw_text")
        }
    return {"approved": False, "perk_score": 0, "title_ru": item.get("title"), "reason": "Сбой оценки"}

def run():
    print("🧠 [Consumer Agent] Фильтрация с помощью LLM-Потребителя...")
    if not os.path.exists(raw_path): return
    with open(raw_path, "r", encoding="utf-8") as f: raw_data = json.load(f)
    
    catalog, today = {}, datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f: catalog = json.load(f)
        except Exception: pass

    rejected_log = []
    if os.path.exists(rejected_path):
        try:
            with open(rejected_path, "r", encoding="utf-8") as f: rejected_log = json.load(f)
        except Exception: pass
            
    for cat, items in raw_data.items():
        catalog.setdefault(cat, [])
        survived = []
        
        for old in catalog[cat]:
            if old.get("added_date") == today:
                survived.append(old)
            elif "valid_until" in old:
                try:
                    if datetime.fromisoformat(old["valid_until"]) > datetime.now():
                        old["is_fresh"] = False
                        survived.append(old)
                except Exception: pass
        
        seen_urls = {x.get("url") for x in survived if x.get("url")}
        
        for it in items:
            if it.get("url") in seen_urls: continue
            
            res = evaluate_single_item(it, cat)
            if res.get("approved"):
                it.update({"title": res["title_ru"], "consumer_reason": res["reason"], "perk_score": res["perk_score"], "is_fresh": True, "added_date": today})
                survived.append(it)
                print(f"  🟢 ОДОБРЕНО [{cat}]: {res['title_ru'][:35]}... | Score: {res['perk_score']}")
            else:
                reason = res.get('reason', 'Не подошло по фильтрам')
                print(f"  🔴 ОТКЛОНЕНО [{cat}]: {it.get('title')[:35]}... -> {reason}")
                rejected_log.append({"date": today, "category": cat, "title": it.get("title"), "reason": reason})
        
        survived.sort(key=lambda x: (1 if x.get("is_fresh") else 0, x.get("perk_score", 0)), reverse=True)
        catalog[cat] = survived
        
    with open(catalog_path, "w", encoding="utf-8") as f: json.dump(catalog, f, ensure_ascii=False, indent=2)
    with open(rejected_path, "w", encoding="utf-8") as f: json.dump(rejected_log[-300:], f, ensure_ascii=False, indent=2)
    print("✅ Каталог и Лог Отказов успешно обновлены!")

if __name__ == "__main__": run()
