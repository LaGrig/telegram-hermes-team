import feedparser

def fetch_rss(url: str, limit: int = 5) -> list[dict]:
    """
    Скачивает RSS-ленту и возвращает список новостей:
    [{title, link, published, summary}, ...]
    """
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        items.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
        })
    return items


if __name__ == "__main__":
    # Тест на публичной ленте
    test_url = "https://feeds.bbci.co.uk/news/rss.xml"
    news = fetch_rss(test_url, limit=3)
    for n in news:
        print(f"- {n['title']} ({n['link']})")
