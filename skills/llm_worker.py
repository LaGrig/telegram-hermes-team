import os
import json
import re
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, ".env")

def load_env():
    env = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env

env = load_env()
API_KEY = env.get("OPENROUTER_API_KEY")
# По умолчанию используем бесплатную Llama 3 8B, но можно переопределить в .env
MODEL = env.get("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct:free")

def ask_llm(system_prompt, user_prompt, expect_json=True):
    if not API_KEY:
        print("❌ ОШИБКА: OPENROUTER_API_KEY не найден в файле .env")
        return {} if expect_json else ""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/hermes-team",
        "X-Title": "Hermes Editor"
    }

    # Жесткий контроль JSON-формата
    sys_content = system_prompt
    if expect_json:
        sys_content += "\n\nВАЖНО: Ответь СТРОГО в формате валидного JSON. Не пиши никакого текста до или после JSON. Начинай ответ сразу с символа '{'."

    messages = [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1  # Минимум креативности, максимум логики
    }

    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        res.raise_for_status()
        reply = res.json()["choices"][0]["message"]["content"].strip()
        
        if expect_json:
            # Чистим от маркдауна (если модель обернула в ```json ... ```)
            match = re.search(r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```', reply, re.DOTALL)
            if match:
                reply = match.group(1)
            
            # Обрезаем всё, что не внутри скобок
            start = reply.find('{')
            end = reply.rfind('}')
            if start != -1 and end != -1:
                reply = reply[start:end+1]
                
            return json.loads(reply)
            
        return reply
        
    except json.JSONDecodeError:
        print(f"⚠️ Ошибка парсинга JSON от модели. Сырой ответ: {reply[:150]}...")
        return {}
    except Exception as e:
        print(f"❌ Ошибка вызова OpenRouter: {e}")
        return {} if expect_json else ""
