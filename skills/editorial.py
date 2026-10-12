import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.use_llm import ask_llm

def send_message(text: str):
    print(f"[EDITORIAL BOT] {text}")

def listen(text: str):
    # 1. Прочитай карту проекта из skills/readme.txt
    project_map = ""
    readme_path = os.path.join(os.path.dirname(__file__), "readme.txt")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            project_map = f.read()
    else:
        project_map = "Карта проекта не найдена."

    # 2. Сделай быстрый запрос для определения намерения
    intent_prompt = f"Определи намерение. Это команда на изменение кода/создание файлов (ответь CODE) или просто вопрос/просьба показать информацию (ответь CHAT)? Текст: {text}"
    intent = ask_llm(intent_prompt, model="nvidia/nemotron-3.5-lightning:free").strip().upper()

    # 3. Если "CODE" в intent
    if "CODE" in intent:
        # Старая логика создания temp_task.py
        # Генерируем скрипт через ask_llm с моделью cohere/north-mini-code:free
        code_prompt = f"Напиши Python-скрипт для выполнения задачи: {text}. Сохрани результат в переменной result или выведи на печать. Не используй входные данные, только код."
        script_content = ask_llm(code_prompt, model="cohere/north-mini-code:free")
        
        temp_path = os.path.join(os.path.dirname(__file__), "temp_task.py")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        send_message(f"Скрипт создан: {temp_path}. Выполняю...")
        try:
            exec_globals = {"send_message": send_message, "ask_llm": ask_llm}
            exec(script_content, exec_globals)
        except Exception as e:
            send_message(f"Ошибка выполнения скрипта: {e}")

    # 4. Если "CHAT" в intent
    elif "CHAT" in intent:
        # НЕ создавай скрипты. Просто сгенерируй текстовый ответ
        chat_prompt = f"Ответь на вопрос пользователя, используя карту проекта. Вопрос: {text}\nКарта: {project_map}"
        answer = ask_llm(chat_prompt, model="nvidia/nemotron-3-ultra-550b-a55b:free")
        send_message(answer)
    
    else:
        send_message("Не удалось определить намерение. Попробуйте перефразировать запрос.")

if __name__ == "__main__":
    # Пример ручного запуска
    if len(sys.argv) > 1:
        listen(" ".join(sys.argv[1:]))
    else:
        print("Usage: python skills/editorial.py <ваш запрос>")
