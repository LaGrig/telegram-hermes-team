def filter_text(text):
    """
    Простейший skill: фильтрует текст.
    Убирает лишние пробелы и переводит в нижний регистр.
    """
    cleaned = text.strip().lower()
    return cleaned


if __name__ == "__main__":
    sample = "   Пример Текста ДЛЯ Фильтрации   "
    print("Исходный текст:", sample)
    print("После фильтрации:", filter_text(sample))
