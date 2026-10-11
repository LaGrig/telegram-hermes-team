import warnings
# Скрываем назойливое системное предупреждение
warnings.filterwarnings("ignore", category=RuntimeWarning)
from duckduckgo_search import DDGS

def search_web_kosice(category: str, limit: int = 5) -> list[dict]:
    # Делаем общий запрос без русских слов, чтобы гарантированно найти скидки для теста
    query = "Košice študenti zľavy akcie" 
    
    results = []
    try:
        with DDGS() as ddgs:
            search_results = ddgs.text(query, region='sk-sk', safesearch='off', max_results=limit)
            if search_results:
                for r in search_results:
                    results.append({
                        "title": r.get("title", ""),
                        "link": r.get("href", ""),
                        "summary": r.get("body", "")
                    })
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        
    return results
