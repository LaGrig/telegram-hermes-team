import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

LLM_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
MODELS_LIST = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free").split(",")

SYSTEM_PROMPT = """Ты — Главред (Оркестратор) Telegram-канала.
Твоя задача — анализировать входящее сообщение и возвращать ИСКЛЮЧИТЕЛЬНО валидный JSON.

ДОСТУПНЫЕ ДЕЙСТВИЯ (ACTIONS):
1. "run_scraper" — параметры: "topic" (что искать).
2. "rewrite_draft" — параметры: "text" (исходный текст поста), "instructions" (пожелания к редактуре).
3. "delete_perk" — параметры: "target" (что удалить).
4. "sniper_publish" — параметры: "topic" (что раздают).
5. "chat" — обычное общение (параметры: нет).

СТРУКТУРА JSON:
{"action": "...", "params": {...}, "reply": "..."}

ПРИМЕРЫ ДЛЯ ОБУЧЕНИЯ:
Вход: Найди свежие скидки на макбуки
Выход: {"action": "run_scraper", "params": {"topic": "скидки на MacBook"}, "reply": "Ищу макбуки."}

Вход:
[ИСХОДНЫЙ ТЕКСТ]:
✅ Отчет Ищейки по запросу «кроссовки»: Скидка 40%
[ЗАДАЧА]:
Переделай, сделай короче и добавь больше огненных эмодзи
Выход: {"action": "rewrite_draft", "params": {"text": "✅ Отчет Ищейки по запросу «кроссовки»: Скидка 40%", "instructions": "Переделай, сделай короче и добавь больше огненных эмодзи"}, "reply": "Понял, забираю текст на переработку!"}
"""

async def analyze_intent(user_text: str) -> dict:
    """Отправляет запрос в LLM с механизмом фоллбэка и возвращает JSON."""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        for model in MODELS_LIST:
            model = model.strip()
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            
            try:
                response = await client.post(f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=15.0)
                response.raise_for_status()
                
                result_text = response.json()["choices"][0]["message"]["content"]
                clean_text = result_text.replace('```json', '').replace('```', '').strip()
                return json.loads(clean_text)
                
            except Exception as e:
                print(f"Ошибка с моделью {model}: {e}")
                continue
        
        return {"action": "chat", "params": {}, "reply": "Мозги Главреда недоступны."}
