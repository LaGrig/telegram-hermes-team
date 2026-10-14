import os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

LLM_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
MODELS_LIST = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free").split(",")

SYSTEM_PROMPT = """Ты — Главный Редактор Telegram-канала студенческих скидок и вакансий в Кошице (Hermes).
Твоя задача — отредактировать пост или дайджест строго по указаниям Шефа.

ПРАВИЛА ФОРМАТИРОВАНИЯ:
1. Используй ТОЛЬКО HTML-теги для Telegram: <b>жирный</b>, <i>курсив</i>, <a href='ссылка'>текст ссылки</a>. НЕ используй Markdown (** или []).
2. Если редактируешь Вечерний Дайджест — ОБЯЗАТЕЛЬНО сохраняй структуру, все рабочие ссылки <a href='...'> и финальную подпись про каталог, если Шеф не просил их удалить.
3. Пиши живо, без воды и клише ("уникальная возможность", "спешите").
4. ВАЖНО: Возвращай ТОЛЬКО готовый текст поста. Никаких вступлений от себя."""

async def rewrite_post(original_text: str, instructions: str) -> str:
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    user_prompt = f"ИСХОДНЫЙ ТЕКСТ (HTML):\n{original_text}\n\nЗАДАЧА ОТ ШЕФА:\n{instructions}"
    
    async with httpx.AsyncClient() as client:
        for model in MODELS_LIST:
            model = model.strip()
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.5
            }
            try:
                response = await client.post(f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=25.0)
                response.raise_for_status()
                result = response.json()["choices"][0]["message"]["content"].strip()
                return result.replace("```html", "").replace("```", "").strip()
            except Exception as e:
                print(f"Ошибка редактора с моделью {model}: {e}")
                continue
        
        return "❌ Ошибка Редактора: Все модели сейчас недоступны."
