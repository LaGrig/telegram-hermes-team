import re

def calculate_perk_score(item):
    """
    Вычисляет Perk Score (0 - 100) на основе 4 параметров:
    V (Value, 0-35) + F (Friction, 0-25) + T (Proximity/Time, 0-20) + S (Flex/Share, 0-20)
    """
    title = item.get("title", "").lower()
    summary = item.get("summary", "").lower()
    cond = item.get("conditions", "").lower()
    price = item.get("price", "").lower()
    cat = item.get("category", "").lower()
    url = item.get("url", "").lower()

    # 1. VALUE (Выгода, 0-35)
    v = 10
    if "0 €" in price or "бесплатно" in price or "zadarmo" in price or "навсегда" in title:
        v = 35
    elif any(x in price or x in title for x in ["-50%", "-60%", "-70%", "1000 €", "289 €", "540 €", "100 $"]):
        v = 28
    elif any(x in price for x in ["2.", "3.", "4.", "5.", "6."]) or "скидка" in price or "€/час" in price:
        v = 20

    # 2. FRICTIONLESS (Легкость получения, 0-25)
    f = 15
    if any(plat in url or plat in cond for plat in ["epicgames.com", "steampowered.com", "gog.com", "github.com", "edx.org", "kaggle.com"]):
        f = 25  # В 1 клик онлайн
    elif "isic" in cond or "студенческ" in cond or "karta" in cond:
        f = 18  # Показ студенческого на кассе
    elif "навынос" in cond or "registr" in cond:
        f = 10  # Требуется действие/регистрация
    elif "žiadosť" in cond or "osobne" in cond:
        f = 5   # Бюрократия

    # 3. TIMELINESS & PROXIMITY (Локация и время, 0-20)
    t = 10
    if any(loc in title or loc in cond or loc in summary for loc in ["jedlíkov", "tuke", "letná", "upjš", "mánesova"]):
        t = 20  # Прямо в студгородке / кампусе
    elif any(loc in title or loc in cond or loc in summary for loc in ["hlavná", "centrum", "gorkého", "kasárenské"]):
        t = 15  # В центре (10 мин на трамвае)
    elif item.get("urgency") in ["hard_deadline", "limited_slots"]:
        t = 18  # Горящий дедлайн

    # 4. FLEX & SHAREABILITY (Социальный вес, 0-20)
    s = 10
    if cat == "games" and ("навсегда" in title or "free" in title):
        s = 20
    elif cat == "jobs" and ("7." in price or "8." in price or "9." in price or "10." in price):
        s = 20  # Жирная ставка
    elif cat == "events" and any(k in title for k in ["divadlo", "kino", "párty", "kulturpark"]):
        s = 17
    elif cat == "food" and "pizza" in title:
        s = 16

    total_score = min(100, max(0, v + f + t + s))
    return total_score

def wave_sort_category(items):
    """
    Дофаминовая волновая сортировка:
    1. Хит (Max Score)
    2-4. Быстрая польза (высокий F и T)
    5. Якорь (2-й лучший скор)
    6-20. Плавный макро-слой и база
    Отсев: score < 40
    """
    scored_items = []
    for it in items:
        score = calculate_perk_score(it)
        if score >= 40:  # Жесткий фильтр шлака
            it["perk_score"] = score
            scored_items.append(it)

    if not scored_items:
        return []

    # Сортируем весь пул по убыванию скора
    scored_items.sort(key=lambda x: x["perk_score"], reverse=True)
    if len(scored_items) <= 5:
        return scored_items

    hit = scored_items[0]
    anchor = scored_items[1]
    remaining = scored_items[2:]

    # 2-4 позиции: отдаем предпочтение удобным и близким
    remaining.sort(key=lambda x: (x.get("conditions", "") + x.get("title", "")).count("Jedlíkov") * 10 + x["perk_score"], reverse=True)
    quick_wins = remaining[:3]
    macro_layer = remaining[3:]

    # Финальная сборка волновой ленты
    wave_feed = [hit] + quick_wins + [anchor] + macro_layer
    return wave_feed[:20]
