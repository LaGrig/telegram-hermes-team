import os
import sys
import json
import re
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def load_catalog():
    if not os.path.exists(catalog_path):
        return {cat: [] for cat in ["food", "events", "tourism", "software", "courses", "games", "jobs"]}
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {cat: [] for cat in ["food", "events", "tourism", "software", "courses", "games", "jobs"]}

def save_catalog(catalog):
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

# 1. ПОДРАБОТКИ (ЖЕСТКИЙ ФИЛЬТР ИНЖЕНЕРОВ И СЕНЬОРОВ)
def fetch_kosice_jobs():
    print("💼 [Jobs] Сбор студенческих подработок в Кошице...")
    jobs = []
    STOP_WORDS = [
        "senior", "lead", "manažér", "manager", "vedúci", "architekt", "director", 
        "5 rokov", "3 roky", "sap", "consultant", "mamičk", "práca na doma", "doma cez",
        "sociálne siete", "finančn", "poradca", "ovb", "partners group", "call centrum",
        "anketár", "tipér", "statik", "inžinier", "projektant", "konštruktér", "lekár",
        "sestra", "právnik", "účtovník", "audit"
    ]
    
    try:
        url = "https://www.profesia.sk/praca/kosice/na-dohodu-brigady/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.ok:
            soup = BeautifulSoup(res.text, "html.parser")
            job_cards = soup.select(".list-row, [data-list-row]")
            for idx, card in enumerate(job_cards):
                title_node = card.select_one(".title, h2 a, a.title")
                salary_node = card.select_one(".label-salary, .salary")
                if not title_node:
                    continue

                title = title_node.get_text(strip=True)
                title_l = title.lower()

                if any(bad in title_l for bad in STOP_WORDS):
                    continue

                href = title_node.get("href", "")
                if not href or href == "/" or "/praca/" not in href:
                    continue

                full_url = href if href.startswith("http") else f"https://www.profesia.sk{href}"
                salary = salary_node.get_text(strip=True) if salary_node else "от 5.50 €/час"

                jobs.append({
                    "id": f"job_real_{idx}_{int(time.time())}",
                    "category": "jobs",
                    "title": f"💼 {title[:50]}",
                    "price": f"**{salary}** (оплата)",
                    "summary": "Официальная подработка в Кошице без требований к опыту. Подходит студентам TUKE/UPJŠ.",
                    "conditions": "Кошице. Оформление по договоренности (Dohoda o brigáde).",
                    "url": full_url,
                    "valid_until": (datetime.now() + timedelta(days=14)).isoformat(),
                    "urgency": "evergreen"
                })
                if len(jobs) >= 15:
                    break
    except Exception as e:
        print(f"⚠️ Ошибка сбора вакансий: {e}")
    return jobs

# 2. ИГРЫ
def fetch_games():
    games = [
        {
            "id": "game_gog_classics",
            "category": "games",
            "title": "🎮 НАВСЕГДА: Культовые игры GOG Free Collection",
            "price": "**0 €** (навсегда)",
            "summary": "Подборка легендарных хитов без DRM (Beneath a Steel Sky, Shadow Warrior, Ultima).",
            "conditions": "GOG.com. Активация на аккаунт в один клик.",
            "url": "https://www.gog.com/partner/free_games",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "game_steam_sales",
            "category": "games",
            "title": "🎮 Скидки до 90% на хиты в Steam",
            "price": "**от 1.49 €** (акции недели)",
            "summary": "Топовые игры с рейтингом выше 85% по цене чашки кофе.",
            "conditions": "Steam. Акции обновляются каждый четверг.",
            "url": "https://store.steampowered.com/specials",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "game_trackmania",
            "category": "games",
            "title": "🎮 Trackmania: Сезонные заезды за 0 €",
            "price": "**0 €** (бесплатно)",
            "summary": "Соревновательные онлайн-гонки на время. Доступно бесплатно в Steam и Ubisoft Connect.",
            "conditions": "Steam / ПК. Полноценная бесплатная версия.",
            "url": "https://store.steampowered.com",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "game_prime_free",
            "category": "games",
            "title": "🎮 Prime Gaming: Ключи для GOG",
            "price": "**0 €** (с пробным периодом)",
            "summary": "Ежемесячные лицензионные ключи для топовых игр с бессрочной привязкой.",
            "conditions": "Amazon Prime Gaming. Активация в аккаунте GOG.",
            "url": "https://gaming.amazon.com",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        }
    ]

    try:
        url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=SK&allowCountries=SK"
        res = requests.get(url, headers=HEADERS, timeout=10)
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
                    end_d = active_offer.get("endDate")
                    v_until = end_d[:19] if end_d else (datetime.now() + timedelta(days=5)).isoformat()
                    games.insert(0, {
                        "id": f"egs_{el.get('id')}",
                        "category": "games",
                        "title": f"🎮 НАВСЕГДА: {title}",
                        "price": f"**0 €** (вместо {orig_p})",
                        "summary": el.get("description", "Официальная бесплатная раздача в Epic Games Store.")[:140] + "...",
                        "conditions": "Epic Games Store. Забирается на личный аккаунт навсегда.",
                        "url": "https://store.epicgames.com/free-games",
                        "valid_until": v_until,
                        "urgency": "hard_deadline"
                    })
                    break
    except Exception:
        pass
    return games

# 3. ЕДА (ЧЕТКОЕ РАЗДЕЛЕНИЕ НА ВЕЧЕР И ОБЕД)
def get_kosice_food():
    return [
        {
            "id": "food_jedlikova_pizza",
            "category": "food",
            "title": "🍕 Пицца навынос на Jedlíkova (Общаги TUKE)",
            "price": "**от 5.50 €** (вечерний перекус)",
            "summary": "Большая горячая пицца прямо в студенческом городке Jedlíkova 5/9.",
            "conditions": "Ежедневно с 16:00 до 22:00. Локация: студгородок Jedlíkova.",
            "url": "https://www.tuke.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen",
            "timing": "evening"
        },
        {
            "id": "food_dve_lave_pizza",
            "category": "food",
            "title": "🍕 Вечерняя скидка в Dve Ľavé (Hlavná)",
            "price": "**-10% на крафтовую пиццу**",
            "summary": "Неаполитанская пицца в самом центре города. Место для вечерних встреч.",
            "conditions": "Hlavná 40. Действует ежедневно после 16:00 при предъявлении ISIC.",
            "url": "https://www.sdke.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen",
            "timing": "evening"
        },
        {
            "id": "food_nico_caffe",
            "category": "food",
            "title": "☕ Кофе + бейгл в Nico Caffe (Коворкинг)",
            "price": "**4.20 €**",
            "summary": "Место для учебы и работы с ноутбуком возле UPJŠ. Розетки и быстрый Wi-Fi.",
            "conditions": "Kuzmányho 1. Открыто до 20:00 в будни.",
            "url": "https://kinousmev.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen",
            "timing": "evening"
        },
        {
            "id": "food_tuke_jedalen",
            "category": "food",
            "title": "🍔 Обед в столовой TUKE (Jedáleň)",
            "price": "**2.80 € – 3.80 €** (госсубсидия по ISIC)",
            "summary": "Горячий комплекс: суп + второе блюдо во всех столовых кампуса TUKE.",
            "conditions": "Пн-Пт с 11:00 до 14:30. Оплата студенческой картой ISIC TUKE.",
            "url": "https://www.tuke.sk/wps/portal/tuke/university",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen",
            "timing": "lunch"
        },
        {
            "id": "food_tuke_buffet",
            "category": "food",
            "title": "🥪 Буфет в главном корпусе TUKE (Letná 9)",
            "price": "**2.20 € – 3.50 €**",
            "summary": "Свежие багеты, выпечка и кофе прямо во время перерывов между парами.",
            "conditions": "Letná 9. Открыто до 16:30 в будние дни.",
            "url": "https://www.tuke.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen",
            "timing": "day"
        }
    ]

# 4. СОБЫТИЯ
def get_kosice_events():
    return [
        {
            "id": "ev_kino_usmev",
            "category": "events",
            "title": "🎬 Студенческий билет в Kino Úsmev",
            "price": "**Скидка 1 € по ISIC** (билет 5 € вместо 6 €)",
            "summary": "Культовый кинотеатр и бар: фестивальное кино, открытая терраса и лекции.",
            "conditions": "Kasárenské námestie 1. Скидка 1 € в кассе или онлайн при выборе студенческого тарифа.",
            "url": "https://kinousmev.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_sdke_theatre",
            "category": "events",
            "title": "🎭 Государственный театр Кошиц (SDKE)",
            "price": "**3 € – 5 €** (скидка до 60% по ISIC)",
            "summary": "Драма, опера и балет в историческом здании на Hlavná ulica.",
            "conditions": "Hlavná 58. Покупка билетов в кассе театра по карте ISIC.",
            "url": "https://www.sdke.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_botanical_garden",
            "category": "events",
            "title": "🌿 Ботанический сад UPJŠ (Оранжереи)",
            "price": "**2 €** (льготный тариф)",
            "summary": "Крупнейший ботсад в Словакии рядом с кампусом TUKE. Тропические оранжереи.",
            "conditions": "Mánesova 23. Скидка при предъявлении студенческого билета.",
            "url": "https://www.upjs.sk/pracoviska/botanicka-zahrada/",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_vsg_gallery",
            "category": "events",
            "title": "🎨 Выставки в Восточнословацкой галерее (VSG)",
            "price": "**0 € – 2 €** (льготный вход)",
            "summary": "Современное визуальное искусство прямо на Главной улице.",
            "conditions": "Hlavná 27. Каждую первую среду месяца вход бесплатный.",
            "url": "https://vsg.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_k13_kulturpark",
            "category": "events",
            "title": "🏛 Kasárne / Kulturpark: Пространство и события",
            "price": "**0 € – 3 €** (студенческий тариф)",
            "summary": "Главный культурный комплекс Кошиц. Огромный парк, мероприятия и коворкинги.",
            "conditions": "Kukučínova 2. Студенческие скидки по карте ISIC.",
            "url": "https://k13.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        }
    ]

# 5. СОФТ, КУРСЫ, ТУРИЗМ (БАЗА ДЛЯ MINI APP)
def get_static_perks():
    software = [
        {
            "id": "soft_gh_pack",
            "category": "software",
            "title": "GitHub Student Developer Pack",
            "price": "**0 €** (экономия > 1000 €)",
            "summary": "Бесплатные домены .me, кредиты DigitalOcean, подписки Datadog и инструменты.",
            "conditions": "Студенческая почта TUKE/UPJŠ или карта ISIC.",
            "url": "https://education.github.com/pack",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "soft_jetbrains",
            "category": "software",
            "title": "Все IDE от JetBrains (All Products Pack)",
            "price": "**0 €** (вместо 289 €/год)",
            "summary": "Лицензии на IntelliJ IDEA Ultimate, PyCharm Pro, WebStorm, CLion на весь срок учебы.",
            "conditions": "Продлевается ежегодно через университетский .edu аккаунт.",
            "url": "https://www.jetbrains.com/community/education/#students",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "soft_autodesk",
            "category": "software",
            "title": "Autodesk Fusion 360 & AutoCAD",
            "price": "**0 €** (вместо 540 €/год)",
            "summary": "CAD/CAM софт для 3D-моделирования, симуляций и черчения.",
            "conditions": "Бесплатно для студентов инженерных специальностей TUKE.",
            "url": "https://www.autodesk.com/education/edu-software/overview",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "soft_notion",
            "category": "software",
            "title": "Notion Plus со всеми функциями",
            "price": "**0 €** (вместо 10 $/мес)",
            "summary": "Неограниченная загрузка файлов, история версий и командный доступ для учебы.",
            "conditions": "Регистрация на университетский e-mail.",
            "url": "https://www.notion.so/product/notion-for-education",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "soft_spotify",
            "category": "software",
            "title": "Spotify Premium Student",
            "price": "**3.49 €/мес** (-50% скидка)",
            "summary": "Музыка без рекламы и офлайн-треки по официальному студенческому тарифу.",
            "conditions": "Подтверждение статуса студента через SheerID раз в год.",
            "url": "https://www.spotify.com/sk/student/",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        }
    ]

    courses = [
        {
            "id": "course_cs50",
            "category": "courses",
            "title": "Гарвардский курс CS50x (Компьютерные науки)",
            "price": "**0 €** (полный курс бесплатно)",
            "summary": "Фундаментальный курс по алгоритмам, C, Python, SQL и веб-разработке.",
            "conditions": "Доступен бесплатно на платформе edX.",
            "url": "https://cs50.harvard.edu/x/",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "course_aws_student",
            "category": "courses",
            "title": "AWS Educate: Облачные курсы и лаборатории",
            "price": "**0 €** + сертификат участника",
            "summary": "Практические треки по Cloud, DevOps и Data Engineering.",
            "conditions": "Регистрация через студенческую почту университета.",
            "url": "https://aws.amazon.com/education/awseducate/",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "course_cisco_skills",
            "category": "courses",
            "title": "Cisco Skills For All: Основы Python и Сетей",
            "price": "**0 €** (с цифровым бейджем)",
            "summary": "Интерактивная практика по сетям, кибербезопасности и скриптингу с нуля.",
            "conditions": "Бесплатно для всех студентов.",
            "url": "https://skillsforall.com",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "course_kaggle",
            "category": "courses",
            "title": "Kaggle Micro-Courses: Data Science & AI",
            "price": "**0 €** (бесплатная практика на GPU)",
            "summary": "Интерактивные микро-курсы по Pandas, Machine Learning и нейросетям.",
            "conditions": "Бесплатно для всех пользователей Kaggle.",
            "url": "https://www.kaggle.com/learn",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "course_freecodecamp",
            "category": "courses",
            "title": "freeCodeCamp: Сертификация по Web & Python",
            "price": "**0 €** (300 часов практики)",
            "summary": "Полный практический трек по Fullstack-разработке и алгоритмам.",
            "conditions": "Открытый доступ без ограничений.",
            "url": "https://www.freecodecamp.org",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        }
    ]

    tourism = [
        {
            "id": "tour_zssk_register",
            "category": "tourism",
            "title": "Бесплатный проезд на поездах по всей Словакии (ZSSK)",
            "price": "**0 €** на все регулярные поезда",
            "summary": "Официальная регистрация на бесплатный студенческий билет (Bezplatná preprava).",
            "conditions": "Оформляется на вокзале Кошиц (Železničná stanica) по справке из вуза и ISIC.",
            "url": "https://www.zssk.sk",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "tour_regiojet",
            "category": "tourism",
            "title": "Скидка до 50% на поезда и автобусы RegioJet",
            "price": "**Скидка до 50%** по Словакии и Чехии",
            "summary": "Студенческие билеты на поезда из Кошиц в Прагу, Брно и Братиславу.",
            "conditions": "Требуется карта ISIC при покупке и контроле в вагоне.",
            "url": "https://regiojet.sk",
            "valid_until": "2026-12-31T23:59:00",
            "urgency": "evergreen"
        },
        {
            "id": "tour_flixbus",
            "category": "tourism",
            "title": "Скидка 10% на все рейсы FlixBus по Европе",
            "price": "**-10%** на любой билет",
            "summary": "Регулярный промокод в мобильном приложении на международные автобусы из Кошиц.",
            "conditions": "Генерируется через личный кабинет ISIC.sk.",
            "url": "https://www.isic.sk",
            "valid_until": "2026-12-31T23:59:00",
            "urgency": "evergreen"
        },
        {
            "id": "tour_leo_express",
            "category": "tourism",
            "title": "Leo Express: Молодежные тарифы со скидкой",
            "price": "**Скидка 25% – 50%**",
            "summary": "Прямые рейсы из Кошиц в Краков, Варшаву и Прагу с Wi-Fi и розетками.",
            "conditions": "Применимо для студентов до 26 лет при наличии ISIC.",
            "url": "https://www.leoexpress.com",
            "valid_until": "2026-12-31T23:59:00",
            "urgency": "evergreen"
        },
        {
            "id": "tour_ryanair_erasmus",
            "category": "tourism",
            "title": "Ryanair Erasmus / ISIC: Скидка 10% + Багаж 20 кг",
            "price": "**-10%** + бесплатный регистрируемый багаж",
            "summary": "Спецтариф на международные перелеты из Кошиц и Будапешта.",
            "conditions": "Регистрация номера ESN / ISIC в профиле myRyanair.",
            "url": "https://www.ryanair.com",
            "valid_until": "2026-12-31T23:59:00",
            "urgency": "evergreen"
        }
    ]
    return software, courses, tourism

def run():
    print("🚀 [Local Scraper] Запуск чистого сбора кандидатов...")
    catalog = {cat: [] for cat in ["food", "events", "tourism", "software", "courses", "games", "jobs"]}

    catalog["jobs"] = fetch_kosice_jobs()
    catalog["games"] = fetch_games()
    catalog["food"] = get_kosice_food()
    catalog["events"] = get_kosice_events()

    soft, courses, tour = get_static_perks()
    catalog["software"] = soft
    catalog["courses"] = courses
    catalog["tourism"] = tour

    save_catalog(catalog)
    print("✅ [Local Scraper] Данные синхронизированы!")

if __name__ == "__main__":
    run()
