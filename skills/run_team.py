import yaml
from filter_text import filter_text
from count_words import count_words

# Загружаем конфиг агентов
with open("agents/team.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

# Находим writer_bot и searcher_bot
writer_bot = next(agent for agent in data["agents"] if agent["name"] == "writer_bot")
searcher_bot = next(agent for agent in data["agents"] if agent["name"] == "searcher_bot")

print("=== Тест взаимодействия агентов Hermes ===")
print(f"Writer Bot: {writer_bot['skills']}")
print(f"Searcher Bot: {searcher_bot['skills']}")

# Исходный текст
sample_text = "   Пример Текста ДЛЯ Фильтрации и подсчёта слов   "
print("\nИсходный текст:", sample_text)

# Writer Bot фильтрует текст
filtered = filter_text(sample_text)
print("После Writer Bot:", filtered)

# Searcher Bot считает слова
word_count = count_words(filtered)
print("После Searcher Bot: количество слов =", word_count)
