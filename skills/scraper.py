import httpx
import xml.etree.ElementTree as ET
import urllib.parse

async def run_smart_scraper(topic: str) -> str:
    """Реальный парсер, ищущий упоминания скидок в интернете."""
    
    # Формируем умный запрос: ищем тему + маркеры выгоды
    query = urllib.parse.quote(f"{topic} (скидка OR акция OR бесплатно OR раздача)")
    url = f"https://news.google.com/rss/search?q={query}&hl=ru&gl=RU&ceid=RU:ru"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            
        root = ET.fromstring(response.text)
        items = root.findall('.//item')[:3] # Берем топ-3 самых свежих результата
        
        if not items:
            return f"❌ Ищейка вернулась ни с чем. По теме «{topic}» сейчас тихо."
        
        report = f"✅ *Находки Ищейки по запросу «{topic}»:*\n\n"
        for i, item in enumerate(items, 1):
            title = item.find('title').text
            link = item.find('link').text
            
            # Чистим заголовок от названия издания в конце
            clean_title = title.rsplit(' - ', 1)[0] if ' - ' in title else title
            report += f"*{i}. {clean_title}*\n🔗 [Читать источник]({link})\n\n"
        
        report += "_Перешли мне любой вариант с инструкциями, и я превращу его в пост!_"
        return report
        
    except Exception as e:
        return f"❌ Ошибка работы сенсоров: {str(e)}"
