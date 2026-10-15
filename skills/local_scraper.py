import os, re, json, requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_path = os.path.join(BASE_DIR, "raw_candidates.json")
SEARCH_QUERIES_FILE = os.path.join(BASE_DIR, "search_queries.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

DLC_STOP_WORDS = ["dlc", "starter pack", "pack", "livery", "liveries", "skin", "soundtrack", "ost", "add-on", "addon", "expansion"]
ADULT_JOB_STOP_WORDS = ["statik", "sestra", "lekár", "inžinier", "stavbyvedúci", "architekt", "účtovník", "manažér", "obchodno-technický", "zvárač", "elektrikár", "montážnik", "kuchár", "šéfkuchár", "sbs", "strážn", "ochrank", "bezpečnostn"]

def is_url_alive(url):
    try:
        res = requests.head(url, headers=HEADERS, timeout=8, allow_redirects=True)
        if res.status_code in [404, 410, 500, 502]: return False
        return True
    except Exception: return False

def search_duckduckgo(query):
    print(f"  🔎 [Search Agent] Ищу: {query}")
    try:
        res = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        for a in soup.select(".result__snippet")[:3]:
            parent = a.find_parent("div", class_="result")
            if not parent: continue
            tnode = parent.select_one(".result__title a")
            lnode = parent.select_one(".result__url")
            if tnode and lnode:
                title = tnode.get_text(strip=True)
                link = lnode.get("href", "").strip()
                if "uddg=" in link:
                    from urllib.parse import unquote
                    link = unquote(link.split("uddg=")[1].split("&")[0])
                else:
                    link = f"https://{link}" if not link.startswith("http") else link
                results.append({"title": title, "url": link, "snippet": a.get_text(strip=True)})
        return results
    except Exception as e:
        print(f"  ⚠️ Сбой Search Agent: {e}")
        return []

def is_dlc_or_pack(title, desc="", itype=""):
    text = f"{title} {desc} {itype}".lower()
    return any(re.search(rf'\b{w}\b', text) for w in DLC_STOP_WORDS)

def is_fulltime_or_specialist(title, salary):
    t_low = title.lower()
    for w in ADULT_JOB_STOP_WORDS:
        if w in t_low and "brigád" not in t_low and "študent" not in t_low:
            return True, f"Взрослая/SBS ('{w}')"
    if "€/мес" in salary and "€/час" not in salary: return True, f"Оклад ({salary})"
    return False, ""

def format_salary(raw):
    if not raw: return ""
    s = re.sub(r'\b[Oo]d\b', 'от', " ".join(raw.split()))
    s = re.sub(r'\b(?:EUR|€)/hod\.?', '€/час', s, flags=re.I)
    return re.sub(r'\b(?:EUR|€)/mesiac\b', '€/мес.', s, flags=re.I)

def fetch_raw_jobs():
    print("💼 [Scraper] Сбор подработок Profesia...")
    jobs = []
    try:
        res = requests.get("https://www.profesia.sk/praca/kosice/na-dohodu-brigady/", headers=HEADERS, timeout=12)
        if res.ok:
            for card in BeautifulSoup(res.text, "html.parser").select(".list-row")[:20]:
                tnode = card.select_one(".title")
                if not tnode: continue
                title = tnode.get_text(strip=True)
                url = tnode.get("href", "")
                if "/praca/" not in url: continue
                full_url = url if url.startswith("http") else f"https://www.profesia.sk{url}"
                sal_node = card.select_one(".label-salary, .salary")
                salary = format_salary(sal_node.get_text(strip=True)) if sal_node else ""
                is_bad, reason = is_fulltime_or_specialist(title, salary)
                if is_bad or not salary: continue
                jobs.append({
                    "id": f"profesia_{full_url.split('/')[-1].split('?')[0]}", "category": "jobs",
                    "title": title, "price": salary, "url": full_url,
                    "raw_text": f"Почасовая подработка: {title}. Ставка: {salary}.",
                    "valid_until": (datetime.now() + timedelta(days=14)).isoformat()
                })
    except Exception: pass
    return jobs

def fetch_raw_courses():
    print("🎓 [Scraper] Динамический поиск курсов (Умный Агент)...")
    courses = []
    
    # Udemy
    try:
        res = requests.get("https://www.udemyfreebies.com/", headers=HEADERS, timeout=10)
        for c in BeautifulSoup(res.text, "html.parser").select(".coupon-name a")[:3]:
            title = c.get_text(strip=True)
            slug = c["href"].rstrip("/").split("/")[-1]
            try:
                out_res = requests.get(f"https://www.udemyfreebies.com/out/{slug}", headers=HEADERS, allow_redirects=True, timeout=8)
                if "udemy.com" in out_res.url:
                    courses.append({"id": f"udemy_{slug}", "category": "courses", "title": f"Udemy 100% OFF: {title}", "price": "0 €", "url": out_res.url, "raw_text": f"Горящий 100% купон на курс: {title}.", "valid_until": (datetime.now() + timedelta(days=3)).isoformat()})
            except Exception: continue
    except Exception: pass

    # Динамические запросы из файла
    queries = []
    if os.path.exists(SEARCH_QUERIES_FILE):
        with open(SEARCH_QUERIES_FILE, "r", encoding="utf-8") as f: queries = json.load(f)
    else:
        queries = ["site:coursera.org free courses students IT language", "site:prometheus.org.ua безкоштовні курси IT дизайн", "IT akadémia Košice bootcamp bezplatné"]
        with open(SEARCH_QUERIES_FILE, "w", encoding="utf-8") as f: json.dump(queries, f, ensure_ascii=False, indent=2)

    for q in queries:
        for sr in search_duckduckgo(q):
            courses.append({"id": f"web_{hash(sr['url'])}", "category": "courses", "title": f"Курс: {sr['title']}", "price": "Бесплатно", "url": sr['url'], "raw_text": f"Сниппет: {sr['snippet']}", "valid_until": (datetime.now() + timedelta(days=7)).isoformat()})
            
    evergreen = [
        {"title": "Cisco Skills for All", "url": "https://skillsforall.com/", "desc": "Кибербезопасность и сети."},
        {"title": "Kaggle Learn", "url": "https://www.kaggle.com/learn", "desc": "Python и Machine Learning."},
        {"title": "Гарвардский курс CS50x", "url": "https://cs50.harvard.edu/x/", "desc": "Основы Computer Science."}
    ]
    for idx, ev in enumerate(evergreen):
        courses.append({"id": f"course_ev_{idx}", "category": "courses", "title": ev["title"], "price": "0 €", "url": ev["url"], "raw_text": ev["desc"], "urgency": "evergreen", "valid_until": "2027-01-01T00:00:00"})
    return courses

def fetch_raw_food_events():
    print("🍔 [Scraper] Сбор еды и ивентов...")
    food = [
        {"id": "food_tabacka", "category": "food", "title": "Вечернее меню в Bistro Tabačka", "price": "от 6.50 €", "raw_text": "Студенческий культурный центр на Gorkého 2.", "url": "https://tabacka.sk", "valid_until": (datetime.now() + timedelta(days=30)).isoformat()},
        {"id": "food_usmev", "category": "food", "title": "Пицца у Kino Úsmev", "price": "от 5.20 €", "raw_text": "Бар и стритфуд на Kasárenské námestie 1.", "url": "https://kinousmev.sk", "valid_until": (datetime.now() + timedelta(days=30)).isoformat()},
        {"id": "food_mc_isic", "category": "food", "title": "Скидки по ISIC в McDonald's", "price": "-30%", "raw_text": "Студенческие комбо при сканировании карты ISIC.", "url": "https://www.mcdonalds.sk/o-nas/isic-a-itic/", "valid_until": (datetime.now() + timedelta(days=30)).isoformat()},
        {"id": "food_subway_isic", "category": "food", "title": "Скидка по ISIC в Subway", "price": "-10%", "raw_text": "Скидка на сабы по карте ISIC.", "url": "https://www.subway.sk/", "valid_until": (datetime.now() + timedelta(days=30)).isoformat()}
    ]
    events = [
        {"id": "ev_usmev", "category": "events", "title": "Кинопоказы в Kino Úsmev по ISIC", "price": "5 €", "raw_text": "Скидка на билеты по студенческому.", "url": "https://kinousmev.sk", "valid_until": (datetime.now() + timedelta(days=30)).isoformat()},
        {"id": "ev_cinema_isic", "category": "events", "title": "Билеты в Cinema City (Aupark)", "price": "-2 €", "raw_text": "Льготный тариф для студентов.", "url": "https://www.cinemacity.sk/cinemas/kosice/1090", "valid_until": (datetime.now() + timedelta(days=30)).isoformat()},
        {"id": "ev_kulturpark", "category": "events", "title": "Kasárne / Kulturpark", "price": "0 €", "raw_text": "Арт-парк, коворкинг и выставки на Kukučínova 2.", "url": "https://k13.sk", "valid_until": (datetime.now() + timedelta(days=30)).isoformat()},
        {"id": "ev_faxcopy", "category": "events", "title": "Печать курсовых в FaxCOPY", "price": "-10%", "raw_text": "Скидка на распечатку.", "url": "https://www.faxcopy.sk/", "valid_until": (datetime.now() + timedelta(days=30)).isoformat()}
    ]
    return food, events

def get_static_catalog():
    print("🌍 [QA Scraper] Префлайт-проверка статических ссылок...")
    software = [
        {"id": "soft_autodesk", "category": "software", "title": "Autodesk Fusion 360 & AutoCAD", "price": "0 €", "raw_text": "Бесплатно по почте вуза.", "url": "https://www.autodesk.com/education/", "urgency": "evergreen"},
        {"id": "soft_jetbrains", "category": "software", "title": "JetBrains All Products Pack", "price": "0 €", "raw_text": "Бесплатные IDE.", "url": "https://www.jetbrains.com/community/education/", "urgency": "evergreen"}
    ]
    tourism = [
        {"id": "tour_zssk", "category": "tourism", "title": "Бесплатные поезда ZSSK", "price": "0 €", "raw_text": "По ISIC.", "url": "https://www.zssk.sk/bezplatna-preprava/studenti/", "urgency": "evergreen"},
        {"id": "tour_lufthansa", "category": "tourism", "title": "Lufthansa Student Fares", "price": "Спец тариф", "raw_text": "Доп. багаж 2x23кг.", "url": "https://www.lufthansa.com/gr/en/local-page/student-fares", "urgency": "evergreen"},
        {"id": "tour_ryanair", "category": "tourism", "title": "Ryanair ESNcard", "price": "-10% + багаж", "raw_text": "Скидка на 4 перелета и багаж.", "url": "https://www.ryanair.com/ie/en/plan-trip/explore/erasmus", "urgency": "evergreen"}
    ]
    return [s for s in software if is_url_alive(s["url"])], [t for t in tourism if is_url_alive(t["url"])]

def run():
    raw = {"jobs": fetch_raw_jobs(), "courses": fetch_raw_courses()}
    food, events = fetch_raw_food_events()
    soft, tour = get_static_catalog()
    raw.update({"food": food, "events": events, "software": soft, "tourism": tour, "games": []})
    with open(raw_path, "w", encoding="utf-8") as f: json.dump(raw, f, ensure_ascii=False, indent=2)

if __name__ == "__main__": run()
