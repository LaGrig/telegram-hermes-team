import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
python_bin = sys.executable

# Гарантируем, что все запускаемые агенты видят корень проекта
env = os.environ.copy()
env["PYTHONPATH"] = BASE_DIR

def run_step(step_name, command):
    print(f"\n▶️ [Конвейер] Шаг: {step_name}...")
    res = subprocess.run(command, cwd=BASE_DIR, env=env)
    if res.returncode != 0:
        print(f"❌ Сбой на шаге '{step_name}'!")
        sys.exit(res.returncode)
    print(f"✅ Шаг '{step_name}' успешно выполнен.")

def main():
    print("🚀 Запуск редакционного цикла Hermes...")
    
    # 1. Локальный скрапер (Кошице + Игры + Подработки)
    run_step("1. Сбор проверенных данных", [python_bin, "skills/local_scraper.py"])
    
    # 2. Трехуровневый жесткий аудитор (TTL, сигнатуры, LLM)
    run_step("2. Аудит актуальности каталога", [python_bin, "skills/auditor.py"])
    
    # 3. Публикация дайджеста в канал (если запущен с флагом --publish)
    if "--publish" in sys.argv:
        run_step("3. Публикация дайджеста в Telegram", [python_bin, "skills/publish_digest.py"])

if __name__ == "__main__":
    main()
