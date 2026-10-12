import os
import sys
import json
import re
import requests
import feedparser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_json_path = os.path.join(BASE_DIR, "raw_news.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StudentBot/1.0"}

def extract_reddit_direct_link(post_data):
    url = post_data.get("url", "")
    if url and not "reddit.com" in url:
        return url
    text = post_data.get("selftext", "")
    found = re.findall(r'https?://(?:store\.steampowered\.com|store\.epicgames\.com|gog\.com)[^\s\)\"]+', text)
    if found:
        return found[0]
    all_links = re.findall(r'https?://[^\s\)\"]+', text)
    for l in all_links:
        if "reddit.com" not in l and "redd.it" not in l:
            return l
    return None

def fetch_reddit_games():
    items = []
    try:
        url = "https://www.reddit.com/r/FreeGameFindings/new.json?limit=10"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            posts = res.json().get("data", {}).get("children", [])
            for p in posts:
                d = p.get("data", {})
                flair = (d.get("link_flair_text") or "").lower()
                if "expired" in flair or "closed" in flair:
                    continue
                direct_url = extract_reddit_direct_link(d)
                if direct_url:
                    items.append({
                        "category": "GAME",
                        "title": d.get("title", ""),
                        "url": direct_url
                    })
    except Exception as e:
        print(f"⚠️ Ошибка Reddit: {e}")
    return items

def fetch_slovakia_news():
    items = []
    queries = [
        "Košice študenti zľava",
        "Košice doprava zľavy",
        "ZSSK študenti Košice",
        "Košice podujatia zadarmo"
    ]
    for q in queries:
        try:
            encoded_q = requests.utils.quote(q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=sk&gl=SK&ceid=SK:sk"
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:4]:
                items.append({
                    "category": "LOCAL",
                    "title": entry.title,
                    "url": entry.link
                })
        except Exception as e:
            print(f"⚠️ Ошибка RSS ({q}): {e}")
    return items

print("🔍 Сборщик собирает новости...")
all_items = fetch_slovakia_news() + fetch_reddit_games()

# Присваиваем стабильные числовые ID
news_db = []
for idx, item in enumerate(all_items, 1):
    item["id"] = idx
    news_db.append(item)

with open(raw_json_path, "w", encoding="utf-8") as f:
    json.dump(news_db, f, ensure_ascii=False, indent=2)

print(f"✅ Собрано {len(news_db)} новостей с проверенными ссылками в raw_news.json")
