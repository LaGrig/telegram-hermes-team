import subprocess
import sys
import os

STEPS = [
    ("1. Сборщик (Searcher)", [sys.executable, "skills/searcher.py"], "raw_news.json"),
    ("2. Тестировщик (Tester)", [sys.executable, "skills/tester.py"], "filtered_news.json"),
    ("3. Писатель (Writer)", [sys.executable, "skills/writer.py"], "draft_post.txt"),
]

def run():
    print("🚀 Запуск конвейера редакции Hermes...\n")
    
    for name, cmd, output_file in STEPS:
        print(f"▶️ Запуск шага: {name}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Сбой на шаге '{name}'!")
            if result.stdout:
                print(f"Лог stdout:\n{result.stdout}")
            if result.stderr:
                print(f"Лог stderr:\n{result.stderr}")
            sys.exit(1)
            
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            print(f"⚠️ Ошибка: шаг '{name}' завершился, но артефакт '{output_file}' пуст или не создан.")
            if result.stdout:
                print(f"Лог шага:\n{result.stdout}")
            sys.exit(1)
            
        print(f"✅ Шаг завершен. Файл '{output_file}' обновлен.\n")
        
    print("🎉 Конвейер успешно отработал!")
    print("📄 Итоговый черновик (draft_post.txt):\n")
    with open("draft_post.txt", "r", encoding="utf-8") as f:
        print(f.read())

if __name__ == "__main__":
    run()
