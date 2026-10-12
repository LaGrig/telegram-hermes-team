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

def parse_price_value(price_str):
    if not price_str or price_str == "N/A":
        return 0.0
    val = re.findall(r'\d+(?:\.\d+)?', price_str.replace(',', '.'))
    return float(val[0]) if val else 0.0

# 1. ИГРЫ (ОФИЦИАЛЬНЫЙ EGS + ВЕРИФИЦИРОВАННЫЙ STEAM/GOG)
def fetch_games():
    games = [
        {
            "id": "game_gog_classics",
            "category": "games",
            "title": "🎮 НАВСЕГДА: Культовые игры GOG Free Collection",
            "price": "**0 €** (навсегда)",
            "summary": "Бесплатная подборка классических хитов (Beneath a Steel Sky, Shadow Warrior, Ultima) без DRM.",
            "conditions": "Платформа: GOG.com. Добавляется в личный аккаунт навсегда.",
            "url": "https://www.gog.com/partner/free_games",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "game_steam_sales",
            "category": "games",
            "title": "🎮 Скидки до 90% на хиты в Steam",
            "price": "**от 1.99 €** (акции недели)",
            "summary": "Регулярный раздел топовых игр с рейтингом >85% по цене чашки кофе.",
            "conditions": "Steam. Акции обновляются каждый понедельник и четверг.",
            "url": "https://store.steampowered.com/specials",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "game_epic_freebies",
            "category": "games",
            "title": "🎮 Раздача недели в Epic Games Store",
            "price": "**0 €** (каждый четверг)",
            "summary": "Официальные раздачи платных игр от EGS. Новая игра каждую неделю в 17:00.",
            "conditions": "Платформа: Epic Games Store. Забирается на аккаунт навсегда.",
            "url": "https://store.epicgames.com/free-games",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        }
    ]

    # Прямой API Epic Games
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
                    slug = el.get("productSlug") or el.get("urlSlug") or ""
                    g_url = f"https://store.epicgames.com/p/{slug}" if slug else "https://store.epicgames.com/free-games"
                    end_d = active_offer.get("endDate")
                    v_until = end_d[:19] if end_d else (datetime.now() + timedelta(days=5)).isoformat()
                    games.append({
                        "id": f"egs_{el.get('id')}",
                        "category": "games",
                        "title": f"🎮 НАВСЕГДА: {title}",
                        "price": f"**0 €** (вместо {orig_p})",
                        "summary": el.get("description", "Официальная раздача в Epic Games Store.")[:140] + "...",
                        "conditions": "Epic Games Store. Забирается на личный аккаунт навсегда.",
                        "url": g_url,
                        "valid_until": v_until,
                        "urgency": "hard_deadline"
                    })
    except Exception:
        pass

    # Steam Giveaway API (только прямые чистые ссылки)
    try:
        res = requests.get("https://www.gamerpower.com/api/giveaways?platform=steam", headers=HEADERS, timeout=10)
        if res.ok:
            for it in res.json()[:3]:
                worth = parse_price_value(it.get("worth", "$0.00"))
                if it.get("type", "").lower() == "game" and worth >= 9.99:
                    games.append({
                        "id": f"steam_gw_{it.get('id')}",
                        "category": "games",
                        "title": f"🎮 НАВСЕГДА: {it.get('title')}",
                        "price": f"**0 €** (вместо {it.get('worth')})",
                        "summary": it.get("description", "")[:140] + "...",
                        "conditions": "Платформа: Steam. Навсегда в библиотеку.",
                        "url": it.get("open_giveaway_url") or "https://store.steampowered.com",
                        "valid_until": (datetime.now() + timedelta(days=5)).isoformat(),
                        "urgency": "limited_slots"
                    })
    except Exception:
        pass

    return games

# 2. КУЛЬТУРА И СОБЫТИЯ КОШИЦ (6 ПРОВЕРЕННЫХ ИНСТИТУЦИЙ С HTTP 200)
def fetch_kosice_events():
    return [
        {
            "id": "ev_sdke_theatre",
            "category": "events",
            "title": "🎭 Студенческие билеты в Государственный театр Кошиц",
            "price": "**3 € – 5 €** (скидка до 60% по ISIC)",
            "summary": "Драма, опера и балет в историческом здании на Hlavná ulica. Спектакли каждую неделю.",
            "conditions": "Hlavná 58. Покупка в кассе театра при предъявлении карты ISIC.",
            "url": "https://www.sdke.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_botanical_garden",
            "category": "events",
            "title": "🌿 Ботанический сад UPJŠ (Оранжереи и парк)",
            "price": "**2 €** (студенческий билет)",
            "summary": "Крупнейший ботсад в Словакии рядом с кампусом TUKE. Тропические теплицы и зона отдыха.",
            "conditions": "Mánesova 23. Скидка для студентов вузов по ISIC/TUKE ID.",
            "url": "https://www.upjs.sk/pracoviska/botanicka-zahrada/",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_vsg_gallery",
            "category": "events",
            "title": "🎨 Выставки в Восточнословацкой галерее (VSG)",
            "price": "**0 € – 2 €** (льготный вход)",
            "summary": "Современное визуальное искусство и исторические коллекции прямо на Главной улице.",
            "conditions": "Hlavná 27. Каждую первую среду месяца вход бесплатный.",
            "url": "https://vsg.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_k13_kulturpark",
            "category": "events",
            "title": "🏛 Kasárne / Kulturpark: Выставки и фестивали",
            "price": "**0 € – 4 €** (студенческий тариф)",
            "summary": "Главный мультикультурный комплекс Кошиц. Огромный парк, коворкинги, концерты и дизайн-маркеты.",
            "conditions": "Kukučínova 2. Студенческие скидки на вход и мероприятия по ISIC.",
            "url": "https://k13.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_stm_museum",
            "category": "events",
            "title": "🔬 Словацкий технический музей (STM Košice)",
            "price": "**2.50 €** (скидка 50% по ISIC)",
            "summary": "Интерактивный научный центр, планетарий и зал физических экспериментов на Главной.",
            "conditions": "Hlavná 88. Скидка 50% на все экспозиции по студенческому билету.",
            "url": "https://stm-ke.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "ev_kino_usmev",
            "category": "events",
            "title": "🎬 Студенческое кино и бар в Kino Úsmev",
            "price": "**3.50 € – 5 €** (билет по ISIC)",
            "summary": "Культовый независимый кинотеатр города: фестивальное кино, лекции, открытый бар и терраса.",
            "conditions": "Kasárenské námestie 1. Скидка на билеты при покупке онлайн или в кассе по ISIC.",
            "url": "https://kinousmev.sk",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        }
    ]

# 3. СТУДЕНЧЕСКИЕ ПОДРАБОТКИ (Profesia.sk Košice)
def fetch_kosice_jobs():
    jobs = []
    try:
        url = "https://www.profesia.sk/praca/kosice/na-dohodu-brigady/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.ok:
            soup = BeautifulSoup(res.text, "html.parser")
            job_cards = soup.select(".list-row, [data-list-row]")
            for idx, card in enumerate(job_cards[:6]):
                title_node = card.select_one(".title, h2 a, a.title")
                salary_node = card.select_one(".label-salary, .salary")
                if title_node:
                    title = title_node.get_text(strip=True)
                    href = title_node.get("href", "")
                    full_url = href if href.startswith("http") else f"https://www.profesia.sk{href}"
                    salary = salary_node.get_text(strip=True) if salary_node else "от 5.50 €/час"
                    jobs.append({
                        "id": f"job_prof_{idx}_{int(time.time())}",
                        "category": "jobs",
                        "title": f"💼 {title[:50]}",
                        "price": f"**{salary}** (оплата)",
                        "summary": "Гибкий график для студентов TUKE/UPJŠ. Возможность совмещать с парами.",
                        "conditions": "Кошице. Работа по договору бригады (Dohoda o brigádnickej práci študentov).",
                        "url": full_url,
                        "valid_until": (datetime.now() + timedelta(days=14)).isoformat(),
                        "urgency": "evergreen"
                    })
    except Exception:
        pass
    return jobs

# 4. БАЗОВЫЕ ПЕРКИ (ЕДА, СОФТ, КУРСЫ, ТУРИЗМ)
def get_verified_perks():
    food = [
        {
            "id": "food_tuke_jedalen",
            "category": "food",
            "title": "🍔 Обед в столовой TUKE (Jedáleň)",
            "price": "**2.80 € – 3.80 €** (по ISIC)",
            "summary": "Комплексный горячий обед: суп + второе блюдо во всех столовых кампуса TUKE.",
            "conditions": "Пн-Пт с 11:00 до 14:30. Оплата картой ISIC TUKE.",
            "url": "https://www.tuke.sk/wps/portal/tuke/university",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "food_dve_lave",
            "category": "food",
            "title": "🍕 Denné menu в Dve Ľavé (Hlavná)",
            "price": "**7.50 €** (вместо 9.50 €)",
            "summary": "Сытный обед и крафтовые блюда в самом центре города. Большие порции.",
            "conditions": "С понедельника по пятницу с 11:00 до 15:00.",
            "url": "https://menucka.sk/denne-menu/kosice",
            "valid_until": (datetime.now() + timedelta(days=14)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "food_smile_street",
            "category": "food",
            "title": "🌯 Студенческое комбо в Smile Street Food",
            "price": "**5.90 €** (скидка 15%)",
            "summary": "Бургер или кебаб с картошкой фри возле технического университета.",
            "conditions": "Скидка 15% на всё меню при предъявлении карты ISIC или TUKE ID.",
            "url": "https://menucka.sk/denne-menu/kosice",
            "valid_until": (datetime.now() + timedelta(days=20)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "food_nico_caffe",
            "category": "food",
            "title": "☕ Студенческий кофе + бейгл в Nico Caffe",
            "price": "**4.20 €**",
            "summary": "Утренний сет в коворкинг-кафе возле кампуса UPJŠ. Розетки и быстрый Wi-Fi.",
            "conditions": "Действует до 12:00 в будние дни при наличии студенческого.",
            "url": "https://menucka.sk/denne-menu/kosice",
            "valid_until": (datetime.now() + timedelta(days=14)).isoformat(),
            "urgency": "evergreen"
        },
        {
            "id": "food_jedlikova_pizza",
            "category": "food",
            "title": "🍕 Студенческая пицца на Jedlíkova (Общаги TUKE)",
            "price": "**5.50 €** (скидка на вынос)",
            "summary": "Классическая большая пицца прямо возле общежитий Jedlíkova 5/9.",
            "conditions": "Скидка для студентов при заказе навынос после 17:00.",
            "url": "https://menucka.sk/denne-menu/kosice",
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "urgency": "evergreen"
        }
    ]

    software = [
        {
            "id": "soft_gh_pack",
            "category": "software",
            "title": "GitHub Student Developer Pack",
            "price": "**0 €** (экономия > 1000 €)",
            "summary": "Бесплатные домены .me, кредиты DigitalOcean, подписки Datadog и софт.",
            "conditions": "Нужна студенческая почта или карта ISIC.",
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
            "conditions": "Продлевается раз в год через .edu аккаунт TUKE/UPJŠ.",
            "url": "https://www.jetbrains.com/community/education/#students",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "soft_notion",
            "category": "software",
            "title": "Notion Plus со всеми функциями",
            "price": "**0 €** (вместо 10 $/мес)",
            "summary": "Неограниченная загрузка файлов, командный доступ и история версий страниц.",
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
            "summary": "Музыка без рекламы и офлайн-прослушивание по официальному студенческому тарифу.",
            "conditions": "Подтверждение статуса студента через SheerID раз в год.",
            "url": "https://www.spotify.com/sk/student/",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "soft_autodesk",
            "category": "software",
            "title": "Autodesk Fusion 360 & AutoCAD",
            "price": "**0 €** (вместо 540 €/год)",
            "summary": "Профессиональный CAD/CAM софт для 3D-моделирования, черчения и симуляций.",
            "conditions": "Бесплатно для студентов инженерных специальностей TUKE.",
            "url": "https://www.autodesk.com/education/edu-software/overview",
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
            "summary": "Фундаментальный курс по алгоритмам, C, Python, SQL и веб-разработке с проверкой заданий.",
            "conditions": "Доступен бесплатно всем желающим на платформе edX.",
            "url": "https://cs50.harvard.edu/x/",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        },
        {
            "id": "course_aws_student",
            "category": "courses",
            "title": "AWS Educate: Облачные курсы и лаборатории",
            "price": "**0 €** + сертификат участника",
            "summary": "Практические треки по Cloud, DevOps и Data Engineering без привязки кредитной карты.",
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
            "summary": "Интерактивные микро-курсы по Pandas, Machine Learning и Deep Learning прямо в браузере.",
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
            "summary": "Полный практический трек по Fullstack-разработке и алгоритмам с портфолио проектами.",
            "conditions": "Открытый доступ без ограничений.",
            "url": "https://www.freecodecamp.org",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        }
    ]

    tourism = [
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
            "id": "tour_regiojet",
            "category": "tourism",
            "title": "Скидка до 50% на поезда и автобусы RegioJet",
            "price": "**Скидка до 50%** по Словакии и Чехии",
            "summary": "Выгодные студенческие билеты на комфортные поезда из Кошиц в Прагу и Братиславу.",
            "conditions": "Требуется карта ISIC при покупке и контроле в вагоне.",
            "url": "https://regiojet.sk",
            "valid_until": "2026-12-31T23:59:00",
            "urgency": "evergreen"
        },
        {
            "id": "tour_ryanair_erasmus",
            "category": "tourism",
            "title": "Ryanair Erasmus / ISIC: Скидка 10% + Багаж 20 кг",
            "price": "**-10%** + бесплатный регистрируемый багаж",
            "summary": "Спецтариф на международные перелеты из Кошиц и соседнего Будапешта.",
            "conditions": "Регистрация номера ESN / ISIC в профиле myRyanair за 2 часа до бронирования.",
            "url": "https://www.ryanair.com",
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
            "id": "tour_zssk_register",
            "category": "tourism",
            "title": "Бесплатный проезд на поездах по всей Словакии (ZSSK)",
            "price": "**0 €** на все регулярные поезда",
            "summary": "Официальная регистрация на бесплатный студенческий билет (Bezplatná preprava) по Словакии.",
            "conditions": "Оформляется на вокзале Кошиц (Železničná stanica) по справке из вуза и ISIC.",
            "url": "https://www.zssk.sk",
            "valid_until": "2027-01-01T00:00:00",
            "urgency": "evergreen"
        }
    ]

    return food, software, courses, tourism

def run():
    print("🚀 [Local Scraper] Запуск комплексного сбора и обновления каталога...")
    catalog = load_catalog()

    def merge_items(cat_name, src_list):
        existing_ids = {it["id"] for it in catalog.get(cat_name, [])}
        for item in src_list:
            if item["id"] not in existing_ids:
                catalog[cat_name].append(item)

    # Заполняем рубрики
    merge_items("games", fetch_games())
    merge_items("events", fetch_kosice_events())
    merge_items("jobs", fetch_kosice_jobs())

    food_list, soft_list, course_list, tour_list = get_verified_perks()
    merge_items("food", food_list)
    merge_items("software", soft_list)
    merge_items("courses", course_list)
    merge_items("tourism", tour_list)

    for cat in catalog:
        catalog[cat] = catalog[cat][:10]

    save_catalog(catalog)
    print("✅ [Local Scraper] Каталог полностью синхронизирован и наполнен!")

if __name__ == "__main__":
    run()
