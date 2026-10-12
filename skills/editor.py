import os
import sys
from skills.use_llm import ask_llm

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
draft_path = os.path.join(BASE_DIR, "draft_post.txt")
manifesto_path = os.path.join(BASE_DIR, "manifesto.md")

if not os.path.exists(draft_path) and os.path.exists("draft_post.txt"):
    draft_path = "draft_post.txt"
    manifesto_path = "manifesto.md"

if not os.path.exists(draft_path):
    print("❌ Ошибка: нет файла draft_post.txt для правки.")
    sys.exit(1)

instruction = " ".join(sys.argv[1:]).strip()
if not instruction:
    print("❌ Ошибка: не переданы указания для правки.")
    sys.exit(1)

with open(draft_path, "r", encoding="utf-8") as f:
    current_draft = f.read().strip()

manifesto_content = ""
if os.path.exists(manifesto_path):
    with open(manifesto_path, "r", encoding="utf-8") as f:
        manifesto_content = f.read()

prompt = f"""Ты — Редактор студенческого Telegram-канала в Кошице.
Тебе дан текущий черновик поста и указания Главреда по правкам.

Текущий черновик:
{current_draft}

Манифест канала:
{manifesto_content}

Указания Главреда:
{instruction}

Задача: Внеси строго требуемые изменения в пост. 
Сохрани общую структуру, ссылки, эмодзи, выделение цен и выгоды жирным шрифтом.
В ответе выведи ТОЛЬКО обновленный текст поста целиком, без вводных фраз и комментариев."""

print("✍️ Редактор вносит правки...")
try:
    updated_post = ask_llm(prompt)
except Exception as e:
    print(f"❌ Ошибка вызова LLM: {e}")
    sys.exit(1)

# Очистка от возможных артефактов маркдауна кода
updated_post = updated_post.replace("```markdown", "").replace("```", "").strip()

with open(draft_path, "w", encoding="utf-8") as f:
    f.write(updated_post)

print("✅ Черновик обновлен!")
print(updated_post)
