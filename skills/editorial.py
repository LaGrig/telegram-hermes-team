import os

def listen():
    # Чтение файла skills/readme.txt
    readme_path = "skills/readme.txt"
    project_map_content = ""
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            project_map_content = f.read()

    prompt = f"""Ты dev_bot..."""

    # Приклеиваем прочитанный текст в конец prompt
    if project_map_content:
        prompt += f"\n\nОБЯЗАТЕЛЬНАЯ КАРТА ПРОЕКТА ДЛЯ ПОИСКА ФАЙЛОВ: {project_map_content}"

    # Дальнейший код отправки prompt в нейросеть...
    # (здесь должен быть твой исходный код обработки prompt)
    pass
