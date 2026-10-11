import os
import requests

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "nemotron-3-ultra-550b-a55b:free" 

def ask_llm(prompt: str, system_role: str = "Ты ИИ-ассистент.") -> str:
    """Универсальный навык: отправляет запрос в бесплатную LLM."""
    if not OPENROUTER_KEY:
        print("❌ OPENROUTER_API_KEY не задан")
        return ""
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_role},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.ok:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return ""
    except Exception:
        return ""

if __name__ == "__main__":
    print("🤖 Ответ LLM:", ask_llm("Напиши коротко: зачем студентам скидки?", "Ты молодежный редактор."))
