import os
import json
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_path = os.path.join(BASE_DIR, "raw_candidates.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "sk,cs;q=0.9,en;q=0.8"
}

def fetch_raw_jobs():
    print("💼 [Scraper] Сбор сырых вакансий с Profesia.sk...")
    jobs = []
    try:
        url = "https://www.profesia.sk/praca/kosice/na-dohodu-brigady/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            job_cards = soup.select(".list-row, [data-list-row]")
            for idx, card in enumerate(job_cards):
                title_node = card.select_one(".title, h2 a, a.title")
                salary_node = card.select_one(".label-salary, .salary")
                if not title_node:
                    continue

                title = title_node.get_text(strip=True)
                href = title_node.get("href", "")
                if not href or href == "/" or "/praca/" not in href:
                    continue

                full_url = href if href.startswith("http") else f"https://www.profesia.sk{href}"
                salary = salary_node.get_text(strip=True) if salary_node else "Ставка не указана"

                jobs.append({
                    "id": f"profesia_{full_url.split('/')[-1].split('?')[0]}",
                    "category": "jobs",
                    "title": title,
                    "price": salary,
                    "raw_text": f"Вакансия: {title}. Оплата: {salary}. Источник: Profesia Košice.",
                    "url": full_url,
                    "valid_until": (datetime.now() + timedelta(days=14)).isoformat()
                })
    except Exception as e:
        print(f"  ⚠️ Ошибка обращения к Profesia: {e}")
    return jobs

def fetch_raw_games():
    games = [
        {
            "id": "game_gog_classics",
            "category": "games",
            "title": "Культовые игры GOG Free Collection",
            "price": "0 € (навсегда)",
            "raw_text": "Раздача классических игр без DRM (Beneath a Steel Sky, Ultima, Shadow Warrior) на GOG.com навсегда.",
            "url": "https://www.gog.com/partner/free_games",
            "valid_until": "2027-01-01T00:00:00"
        },
        {
            "id": "game_steam_sales",
            "category": "games",
            "title": "Скидки до 90% на хиты в Steam",
            "price": "от 1.49 €",
            "raw_text": "Акции недели на популярные кооперативные и синглплеерные игры в Steam.",
            "url": "https://store.steampowered.com/specials",
            "valid_until": "2027-01-01T00:00:00"
        }
    ]
    try:
        url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=SK&allowCountries=SK"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.ok:
            elements = res.json().get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
            for el in elements:
                promotions = el.get("promotions") or {}
                offers = promotions.get("promotionalOffers", [])
                if not offers:
                    continue
                active_offer = None
                for off_group in offers:
                    for off in off_group.get("promotionalOffers", []):
                        if off.get("discountSetting", {}).get("discountPercentage") == 0:
                            active_offer = off
                            break
                if active_offer:
                    title = el.get("title", "")
                    orig_cents = el.get("price", {}).get("totalPrice", {}).get("originalPrice", 0)
                    orig_p = f"{orig_cents / 100:.2f} €" if orig_cents > 0 else "Платная игра"
                    games.insert(0, {
                        "id": f"egs_{el.get('id')}",
                        "category": "games",
                        "title": f"Бесплатная раздача EGS: {title}",
                        "price": f"0 € (вместо {orig_p})",
                        "raw_text": f"Игра {title} раздается бесплатно в Epic Games Store вместо {orig_p}. {el.get('description', '')[:120]}",
                        "url": "https://store.epicgames.com/free-games",
                        "valid_until": (datetime.now() + timedelta(days=5)).isoformat()
                    })
                    break
    except Exception:
        pass
    return games

def fetch_raw_food_and_events():
    food = [
        {
            "id": "food_tabacka_bistro",
            "category": "food",
            "title": "Вечернее меню и крафт в Bistro Tabačka",
            "price": "от 6.50 €",
            "raw_text": "Культовый студенческий центр Tabačka Kulturfabrik на Gorkého 2. Кухня открыта до 22:00, бар до 23:00.",
            "url": "https://tabacka.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat()
        },
        {
            "id": "food_tuke_jedalen",
            "category": "food",
            "title": "Обед в столовой TUKE (Jedáleň)",
            "price": "2.80 € – 3.80 € по ISIC",
            "raw_text": "Горячий комплексный обед (суп + второе) в столовых кампуса TUKE. Время работы: с 11:00 до 14:30.",
            "url": "https://www.tuke.sk/wps/portal/tuke/university",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat()
        },
        {
            "id": "food_kino_usmev_bar",
            "category": "food",
            "title": "Пицца и напитки в баре Kino Úsmev",
            "price": "от 5.20 €",
            "raw_text": "Крафтовая пицца и открытый бар возле парка на Kasárenské námestie 1. Работает весь вечер до полуночи.",
            "url": "https://kinousmev.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat()
        }
    ]

    events = [
        {
            "id": "ev_kino_usmev",
            "category": "events",
            "title": "Студенческий кинопоказ в Kino Úsmev",
            "price": "5 € по ISIC (скидка 1 €)",
            "raw_text": "Независимое кино, фестивали и дискуссии в историческом кинотеатре на Kasárenské námestie 1.",
            "url": "https://kinousmev.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat()
        },
        {
            "id": "ev_k13_kulturpark",
            "category": "events",
            "title": "Kasárne / Kulturpark: выставки и парковая зона",
            "price": "0 € – 3 €",
            "raw_text": "Арт-пространство, выставки, парковая зона и открытые коворкинги на Kukučínova 2.",
            "url": "https://k13.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat()
        }
    ]
    return food, events

def get_static_catalog():
    software = [
        {
            "id": "soft_gh_pack",
            "category": "software",
            "title": "GitHub Student Developer Pack",
            "price": "0 € (экономия > 1000 €)",
            "raw_text": "Бесплатные домены, инструменты, доступ к сервисам облака для студентов вузов.",
            "url": "https://education.github.com/pack",
            "valid_until": "2027-01-01T00:00:00"
        },
        {
            "id": "soft_jetbrains",
            "category": "software",
            "title": "JetBrains All Products Pack для студентов",
            "price": "0 € (вместо 289 €/год)",
            "raw_text": "Бесплатные лицензии на IntelliJ, PyCharm, WebStorm, CLion на весь период учебы по студенческой почте.",
            "url": "https://www.jetbrains.com/community/education/#students",
            "valid_until": "2027-01-01T00:00:00"
        }
    ]
    courses = [
        {
            "id": "course_cs50",
            "category": "courses",
            "title": "Гарвардский курс CS50x по Computer Science",
            "price": "0 €",
            "raw_text": "Бесплатный курс по программированию, алгоритмам и веб-разработке на edX.",
            "url": "https://cs50.harvard.edu/x/",
            "valid_until": "2027-01-01T00:00:00"
        }
    ]
    tourism = [
        {
            "id": "tour_zssk_register",
            "category": "tourism",
            "title": "Бесплатные поезда по Словакии (ZSSK)",
            "price": "0 €",
            "raw_text": "Регистрация на бесплатный проезд по студенческой карточке ISIC в кассах вокзала Кошиц.",
            "url": "https://www.zssk.sk",
            "valid_until": "2027-01-01T00:00:00"
        }
    ]
    return software, courses, tourism

def run():
    print("🚀 [Scraper] Сбор сырых кандидатов со всех источников...")
    raw_data = {cat: [] for cat in ["jobs", "games", "food", "events", "software", "courses", "tourism"]}
    
    raw_data["jobs"] = fetch_raw_jobs()
    raw_data["games"] = fetch_raw_games()
    
    food, events = fetch_raw_food_and_events()
    raw_data["food"] = food
    raw_data["events"] = events

    soft, courses, tour = get_static_catalog()
    raw_data["software"] = soft
    raw_data["courses"] = courses
    raw_data["tourism"] = tour

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in raw_data.values())
    print(f"✅ [Scraper] Собрано {total} сырых кандидатов -> сохранены в raw_candidates.json")

if __name__ == "__main__":
    run()
