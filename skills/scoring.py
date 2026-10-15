import re

def calculate_perk_score(item):
    title = item.get("title", "").lower()
    summary = item.get("summary", "").lower()
    cond = item.get("conditions", "").lower()
    price = item.get("price", "").lower()
    cat = item.get("category", "").lower()
    url = item.get("url", "").lower()

    v = 10
    if "0 €" in price or "бесплатно" in price or "zadarmo" in price or "навсегда" in title: v = 35
    elif any(x in price or x in title for x in ["-50%", "-60%", "-70%"]): v = 28
    elif any(x in price for x in ["2.", "3.", "4.", "5.", "6."]) or "скидка" in price or "€/час" in price: v = 20

    f = 15
    if any(plat in url or plat in cond for plat in ["epicgames.com", "steampowered.com", "gog.com", "udemy.com"]): f = 25
    elif "isic" in cond or "студенческ" in cond: f = 18

    t = 10
    if any(loc in title or loc in cond or loc in summary for loc in ["jedlíkov", "tuke", "letná"]): t = 20
    elif any(loc in title or loc in cond or loc in summary for loc in ["hlavná", "centrum", "gorkého"]): t = 15

    s = 10
    if cat == "games" and ("навсегда" in title or "free" in title): s = 20
    elif cat == "jobs" and ("7." in price or "8." in price or "9." in price): s = 20
    
    return min(100, max(0, v + f + t + s))

def wave_sort_category(items):
    # Разделяем рекламные посты и обычные
    ad_items = [it for it in items if it.get("is_ad")]
    regular_items = [it for it in items if not it.get("is_ad")]
    
    scored_items = []
    for it in regular_items:
        score = calculate_perk_score(it)
        if score >= 40:
            it["perk_score"] = score
            scored_items.append(it)
            
    scored_items.sort(key=lambda x: (1 if x.get("is_fresh") else 0, x.get("perk_score", 0)), reverse=True)
    
    # Рекламные посты всегда вставляются на самый верх!
    return ad_items + scored_items
