import os
import requests

# Скачиваем JSON с моделями
response = requests.get("https://openrouter.ai/api/v1/models")
data = response.json()

# Находим ID бесплатных моделей (pricing prompt и completion равны 0)
free_models = []
for model in data.get("data", []):
    pricing = model.get("pricing", {})
    prompt_price = float(pricing.get("prompt", 0))
    completion_price = float(pricing.get("completion", 0))
    if prompt_price == 0 and completion_price == 0:
        free_models.append(model.get("id", ""))

# Собираем в одну строку
models_string = ", ".join(free_models)

# Отправляем в Telegram
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = "-5457457789"
url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": f"Бесплатные модели OpenRouter: {models_string}"
}
requests.post(url, json=payload)
print("Готово! Отправлено в Telegram.")
