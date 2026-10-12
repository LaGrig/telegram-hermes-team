import os
import requests
import json
import time

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_live_free_models():
    """Динамически запрашивает актуальный список доступных бесплатных моделей у OpenRouter."""
    try:
        res = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        if res.status_code == 200:
            models_data = res.json().get("data", [])
            # Фильтруем только активные бесплатные модели
            free_models = [
                m["id"] for m in models_data 
                if m.get("id", "").endswith(":free") or 
                (isinstance(m.get("pricing"), dict) and str(m["pricing"].get("prompt")) == "0")
            ]
            return free_models[:10]
    except Exception:
        pass
    # Резервный список на случай сетевого сбоя каталога
    return [
        "openrouter/free",
        "nvidia/nemotron-3.5-lightning:free",
        "deepseek/deepseek-r1:free",
        "meta-llama/llama-3.3-70b-instruct:free"
    ]

def ask_llm(prompt, system_prompt="Ты полезный ассистент.", model=None):
    if not OPENROUTER_API_KEY:
        raise ValueError("Не задана переменная окружения OPENROUTER_API_KEY")

    # Формируем пул моделей: сначала запрошенная или openrouter/free, затем живые бесплатные модели
    models_pool = []
    if model:
        models_pool.append(model)
    models_pool.append("openrouter/free")
    
    live_models = get_live_free_models()
    for m in live_models:
        if m not in models_pool:
            models_pool.append(m)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram.org",
        "X-Title": "Hermes Student Bot"
    }

    last_error = ""
    for current_model in models_pool:
        try:
            payload = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=40
            )

            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    if content:
                        return content
                last_error = f"{current_model}: пустой ответ"
            else:
                last_error = f"{current_model}: HTTP {res.status_code}"
        except Exception as e:
            last_error = f"{current_model}: {str(e)}"

        time.sleep(1)

    raise RuntimeError(f"Все доступные модели вернули ошибку. Последняя: {last_error}")

if __name__ == "__main__":
    print("Проверка связи с LLM...")
    try:
        reply = ask_llm("Ответь одним словом: Готово")
        print(f"✅ Успех: {reply}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
