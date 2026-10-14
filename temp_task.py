import os

FILE_PATH = "draft_post.txt"

def main():
    if not os.path.exists(FILE_PATH):
        print(f"[ERROR] Файл '{FILE_PATH}' не найден в рабочей директории: {os.getcwd()}")
        return

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        print(content)
    except Exception as e:
        print(f"[ERROR] Не удалось прочитать файл: {e}")

if __name__ == "__main__":
    main()