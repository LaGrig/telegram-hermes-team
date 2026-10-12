import requests
import json

def main():
    url = "https://openrouter.ai/api/v1/models"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Ошибка при парсинге JSON: {e}")
        return
    
    models_data = data.get('data', [])
    free_models = []
    
    for model in models_data:
        pricing = model.get('pricing', {})
        prompt_price = pricing.get('prompt')
        completion_price = pricing.get('completion')
        
        # Проверяем, что оба поля равны '0' (строка) или 0 (число)
        is_free_prompt = prompt_price == '0' or prompt_price == 0
        is_free_completion = completion_price == '0' or completion_price == 0
        
        if is_free_prompt and is_free_completion:
            model_id = model.get('id')
            if model_id:
                free_models.append(model_id)
    
    for model_id in free_models:
        print(model_id)

if __name__ == "__main__":
    main()
