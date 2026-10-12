import os
import subprocess

def run_git_command(command: list) -> bool:
    """Выполняет Git-команду и возвращает статус успеха."""
    try:
        subprocess.run(command, check=True, text=True, capture_output=True)
        print(f"✅ Успешно: {' '.join(command)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка Git: {e.stderr}")
        return False

def dev_autofix(task_description: str, file_to_edit: str, new_content: str = None):
    """
    Навык dev_bot: Вносит изменения в файл и автономно коммитит их на GitHub.
    """
    print(f"👨‍💻 dev_bot выполняет задачу: {task_description}")

    # Перезаписываем файл, если передано новое содержимое
    if new_content :
        with open(file_to_edit, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"📝 Файл {file_to_edit} обновлен.")

    # Добавляем изменения, коммитим и пушим в ветку main
    if run_git_command(["git", "add", file_to_edit]):
        commit_message = f"dev_bot: {task_description}"
        if run_git_command(["git", "commit", "-m", commit_message]):
            run_git_command(["git", "push", "origin", "main"])

if __name__ == "__main__":
    # Локальный тест: dev_bot сам добавляет тестовую строку в team.yaml
    print("Тестируем навык автономного разработчика...")
    target_file = "agents/team.yaml"
    
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    test_string = "\n# Тестовое обновление от dev_bot (проверка связи)\n"
    if test_string not in content:
        new_content = content + test_string
        dev_autofix("добавлена тестовая метка", target_file, new_content)
    else:
        print("Тестовая метка уже есть. Бот работает корректно.")
