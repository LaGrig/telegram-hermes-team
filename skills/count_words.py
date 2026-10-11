def count_words(text):
    """
    Skill: подсчёт слов в тексте.
    Возвращает количество слов.
    """
    words = text.strip().split()
    return len(words)


if __name__ == "__main__":
    sample = "Пример текста для подсчёта количества слов"
    print("Исходный текст:", sample)
    print("Количество слов:", count_words(sample))
