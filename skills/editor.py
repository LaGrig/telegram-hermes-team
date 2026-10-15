import os, json, httpx, re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
MODELS_LIST = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free").split(",")
ADMIN_STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_state.json")
CATALOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog_perks.json")
REJECTED_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rejected_log.json")
SEARCH_QUERIES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "search_queries.json")

EDITOR_PERSONA = """Ты — Главный Редактор канала Hermes Košice. Общаешься со своим создателем (LaGrig). 
Отвечай СТРОГО на русском языке. Использование английского запрещено.
Знаешь всю внутреннюю кухню: 
- Расписание: 16:40 (парсинг), 17:00 (Вечерний дайджест), 03:00 (Аудит и чистка)."""

async def llm_request(prompt: str, sys_prompt: str = EDITOR_PERSONA) -> str:
    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        for model in MODELS_LIST:
            payload = {"model": model.strip(), "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}], "temperature": 0.7}
            try:
                res = await client.post(f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=15.0)
                res.raise_for_status()
                return res.json()["choices"][0]["message"]["content"].strip()
            except Exception: continue
    return "❌ Ошибка связи с нейросетью."

def load_admin_state():
    if os.path.exists(ADMIN_STATE_FILE):
        with open(ADMIN_STATE_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {"step": "idle", "draft": {}}

def save_admin_state(state):
    with open(ADMIN_STATE_FILE, "w", encoding="utf-8") as f: json.dump(state, f, ensure_ascii=False)

async def generate_rejection_report() -> dict:
    if not os.path.exists(REJECTED_LOG_FILE):
        return {"text": "Шеф, лог отказов пуст.", "buttons": []}
    with open(REJECTED_LOG_FILE, "r", encoding="utf-8") as f:
        try: log = json.load(f)
        except Exception: log = []
    
    if not log: return {"text": "Шеф, лог отказов пуст. Всё чисто.", "buttons": []}
        
    recent = log[-40:]
    log_text = "\n".join([f"- [{item['category']}] {item['title']} (Причина: {item['reason']})" for item in recent])
    
    sys_prompt = "Ты SMM-аналитик. Отвечай коротко, жестко и по-деловому. Строго на русском."
    prompt = f"Проанализируй список отбракованных новостей:\n{log_text}\n\nВыдели 1-2 главные тенденции. Сформулируй 3-5 стоп-слов для фильтра."
    report = await llm_request(prompt, sys_prompt)
    return {"text": f"📊 <b>ЕЖЕНЕДЕЛЬНАЯ ПЛАНЕРКА</b>\n\n{report}", "buttons": [("🗑 Очистить лог мусора", "CLEAR_REJECT_LOG")]}

def clear_rejection_log():
    if os.path.exists(REJECTED_LOG_FILE): os.remove(REJECTED_LOG_FILE)

async def chat_with_editor(user_message: str) -> dict:
    state = load_admin_state()
    
    # 1. ОБРАБОТКА ИНЛАЙН-КНОПОК (Реклама / Дайджест)
    if state["step"] == "wait_action":
        if user_message == "PUBLISH_TOP":
            state["step"] = "wait_top_days"
            save_admin_state(state)
            return {"text": "На сколько дней закрепить пост в TOP (напиши цифру)?", "buttons": []}
        elif user_message == "PUBLISH_DIGEST":
            draft = state["draft"]
            draft["perk_score"], draft["is_fresh"] = 100, True
            cat_data = {}
            if os.path.exists(CATALOG_FILE):
                with open(CATALOG_FILE, "r", encoding="utf-8") as f: cat_data = json.load(f)
            cat_name = draft.get("category", "events")
            cat_data.setdefault(cat_name, [])
            cat_data[cat_name].insert(0, draft)
            with open(CATALOG_FILE, "w", encoding="utf-8") as f: json.dump(cat_data, f, ensure_ascii=False, indent=2)
            state["step"] = "idle"
            save_admin_state(state)
            return {"text": "✅ Пост добавлен. Сегодня в 17:00 он автоматически уйдет в Дайджест!", "buttons": []}
        elif user_message == "CANCEL":
            state["step"] = "idle"
            save_admin_state(state)
            return {"text": "Отменил.", "buttons": []}
            
    if state["step"] == "wait_top_days":
        try:
            days = int(user_message.strip())
            draft = state["draft"]
            draft["is_ad"] = True
            draft["ad_until"] = (datetime.now() + timedelta(days=days)).isoformat()
            
            cat_data = {}
            if os.path.exists(CATALOG_FILE):
                with open(CATALOG_FILE, "r", encoding="utf-8") as f: cat_data = json.load(f)
            cat_name = draft.get("category", "events")
            cat_data.setdefault(cat_name, [])
            cat_data[cat_name].insert(0, draft)
            with open(CATALOG_FILE, "w", encoding="utf-8") as f: json.dump(cat_data, f, ensure_ascii=False, indent=2)
            state["step"] = "idle"
            save_admin_state(state)
            return {"text": f"🔥 Рекламный пост успешно закреплен в TOP на {days} дней.", "buttons": []}
        except ValueError:
            return {"text": "Напиши просто число (например: 7).", "buttons": []}

    # 2. НОВАЯ ЛОГИКА: ДИНАМИЧЕСКИЙ ПОИСК (Добавление источников)
    if any(k in user_message.lower() for k in ["монитор", "искать", "ищи ", "добавь источник", "начни искать", "гугли"]):
        sys_prompt = 'Ты SEO-специалист. Шеф просит добавить новый источник. Сформулируй 1 идеальный поисковый запрос для DuckDuckGo (используй site: если указан сайт, например site:epam.com). Верни СТРОГО JSON: {"action": "add_source", "query": "твой запрос", "reply": "Ответ шефу"}'
        response = await llm_request(user_message, sys_prompt)
        try:
            json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
            data = json.loads(json_str)
            if data.get("action") == "add_source":
                query = data["query"]
                queries = []
                if os.path.exists(SEARCH_QUERIES_FILE):
                    with open(SEARCH_QUERIES_FILE, "r", encoding="utf-8") as f: queries = json.load(f)
                else:
                    queries = ["site:coursera.org free courses students IT language", "site:prometheus.org.ua безкоштовні курси IT дизайн"]
                
                if query not in queries:
                    queries.append(query)
                    with open(SEARCH_QUERIES_FILE, "w", encoding="utf-8") as f: json.dump(queries, f, ensure_ascii=False, indent=2)
                return {"text": f"🔎 <b>Поисковая база обновлена!</b>\n\n{data.get('reply', 'Запрос добавлен.')}\n<i>Добавлен вектор:</i> <code>{query}</code>", "buttons": []}
        except Exception: pass

    # 3. ПОЛУЧЕНА ССЫЛКА (ЧЕРНОВИК)
    if "http" in user_message or "подготовь пост" in user_message.lower() or "дайджест" in user_message.lower():
        sys_prompt = 'Верни строго JSON: {"title": "Заголовок", "price": "Цена", "raw_text": "Описание", "url": "Ссылка", "category": "food/jobs/events/courses/software/tourism/games"}'
        response = await llm_request(user_message, sys_prompt)
        try:
            json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
            draft = json.loads(json_str)
            draft["id"] = f"custom_{datetime.now().timestamp()}"
            state["step"] = "wait_action"
            state["draft"] = draft
            save_admin_state(state)
            preview = f"📝 <b>ЧЕРНОВИК:</b>\n\n📌 <b>{draft['title']}</b>\n💰 {draft['price']}\nℹ️ {draft['raw_text']}\n🔗 <a href='{draft['url']}'>Ссылка</a>\n\nКатегория: {draft['category']}\n\nШеф, что делаем с постом?"
            return {"text": preview, "buttons": [("Включить в Дайджест 17:00", "PUBLISH_DIGEST"), ("Сделать TOP (Реклама)", "PUBLISH_TOP"), ("Отмена", "CANCEL")]}
        except Exception: pass

    # 4. ОБЫЧНЫЙ ЧАТ
    answer = await llm_request(user_message)
    return {"text": answer, "buttons": []}
