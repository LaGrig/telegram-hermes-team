import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
python_bin = sys.executable
env = os.environ.copy()
env["PYTHONPATH"] = BASE_DIR

def run_step(step_name, command):
    print(f"\n▶️ [Конвейер] Шаг: {step_name}...")
    res = subprocess.run(command, cwd=BASE_DIR, env=env)
    if res.returncode != 0:
        print(f"🛑 [СТОП] Сбой на шаге '{step_name}'. Конвейер остановлен.")
        sys.exit(res.returncode)
    print(f"✅ Шаг '{step_name}' успешно выполнен.")

def main():
    print("🚀 Запуск агентного конвейера Hermes Team...")
    
    run_step("1. Сбор сырых данных (Scraper)", [python_bin, "skills/local_scraper.py"])
    run_step("2. Оценка контента Агентом-Потребителем (LLM QA)", [python_bin, "skills/agent_consumer.py"])
    run_step("3. Редколлегия (Editorial Board)", [python_bin, "skills/editorial.py"])
    run_step("4. Префлайт-контроль ссылок (Quality Gate)", [python_bin, "skills/quality_gate.py"])
    
    # 5. Финальная публикация
    if "--publish" in sys.argv:
        run_step("5. Публикация в Telegram (Publisher)", [python_bin, "skills/publisher.py"])
    else:
        print("\nℹ️ Запуск без публикации. Чтобы отправить пост в канал, добавьте флаг --publish")

if __name__ == "__main__":
    main()
