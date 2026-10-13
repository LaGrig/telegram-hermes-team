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
        print(f"🛑 [СТОП] Сбой на шаге '{step_name}'. Публикация заблокирована.")
        sys.exit(res.returncode)
    print(f"✅ Шаг '{step_name}' успешно выполнен.")

def main():
    print("🚀 Запуск редакционного цикла Hermes с префлайт-контролем...")
    
    # 1. Сборщик
    run_step("1. Сбор проверенных данных", [python_bin, "skills/local_scraper.py"])
    
    # 2. Аудитор и Скоринг
    run_step("2. Технический аудит и Perk Score", [python_bin, "skills/auditor.py"])
    
    # 3. Редколлегия (Формирование выпуска)
    run_step("3. Редколлегия (Editorial Board)", [python_bin, "skills/editorial.py"])
    
    # 4. БЛОКИРУЮЩИЙ КОНТРОЛЬ КАЧЕСТВА (Quality Gate)
    run_step("4. Префлайт-контроль ссылок и фактов", [python_bin, "skills/quality_gate.py"])
    
    # 5. Публикация в канал
    if "--publish" in sys.argv:
        run_step("5. Публикация верифицированного выпуска", [python_bin, "skills/publish_digest.py"])

if __name__ == "__main__":
    main()
