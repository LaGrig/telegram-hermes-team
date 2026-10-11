import yaml
from filter_text import filter_text

# Загружаем конфиг агентов
with open("agents/team.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

# Находим writer_bot
writer_bot = next(agent for agent in data["agents"] if agent["name"] == "writer_bot")

print("Агент:", writer_bot["name"])
print("Роль:", writer_bot["role"])
print("Skills:", writer_bot["skills"])

# Тестируем skill filter_text
sample_text = "   Пример Текста ДЛЯ Фильтрации   "
result = filter_text(sample_text)
print("\nИсходный текст:", sample_text)
print("После работы skill:", result)
