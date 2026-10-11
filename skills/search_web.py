from duckduckgo_search import DDGS

def search_web_kosice(category: str, limit: int = 5) -> list[dict]:
    """
    Ищет актуальные предложения для студентов в Кошице по заданной категории.
    Использует гео-настройки Словакии (sk-sk) для релевантной выдачи.
    """
    # Формируем целевой запрос
    query = f"Košice študenti zľavy akcie {category}"
    results = []
    
    try:
        with DDGS() as ddgs:
            # Ищем в вебе с привязкой к региону Словакии
            search_results = ddgs.text(query, region='sk-sk', safesearch='off', max_results=limit)
            
            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "summary": r.get("body", "")
                })
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        
    return results

if __name__ == "__main__":
    # Локальный тест
    print("Тест поиска для 'Еда и промокоды':")
    news = search_web_kosice("jedlo reštaurácie", limit=3)
    for item in news:
        print(f"\nНазвание: {item['title']}\nОписание: {item['summary']}\nСсылка: {item['link']}")
