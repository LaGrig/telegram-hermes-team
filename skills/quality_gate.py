import re
import sys
import requests
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def verify_url_live(url):
    """Проверяет реальную доступность ссылки и отсутствие редиректа на корень."""
    parsed = urlparse(url)
    # 1. Запрет ссылок на корень агрегаторов
    if parsed.path in ["", "/"] and parsed.netloc in ["www.profesia.sk", "profesia.sk", "menucka.sk"]:
        return False, "Ссылка ведет на главную страницу портала, а не на конкретный оффер"

    # 2. HTTP проверка
    try:
        res = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        if res.status_code in [404, 410]:
            return False, f"HTTP {res.status_code} (Битая ссылка)"
        if res.status_code >= 500:
            return False, f"HTTP {res.status_code} (Сервер недоступен)"
        
        # Проверка страниц 404 у Epic Games и SPA-приложений
        content = res.text.lower()
        if "page not found" in content or "stránka sa nenašla" in content or "404 - " in content:
            return False, "Страница отдала ошибку 404 внутри интерфейса"

        return True, "OK"
    except Exception as e:
        return False, f"Сбой сети при переходе: {str(e)[:40]}"

def inspect_draft(draft_text):
    print("🛡 [Quality Gate] Инспектор качества проверяет черновик перед печатью...")
    links = re.findall(r'<a href=[\'"](.*?)[\'"]>', draft_text)
    
    if len(links) < 3:
        return False, f"В дайджесте меньше 3 ссылок ({len(links)} найдено)."

    errors = []
    for idx, url in enumerate(links, 1):
        is_valid, reason = verify_url_live(url)
        if not is_valid:
            errors.append(f"Пункт #{idx} ({url}): {reason}")

    if errors:
        print("❌ [Quality Gate] ПРЕФЛАЙТ НЕ ПРОЙДЕН! Обнаружен брак:")
        for err in errors:
            print(f"   ⛔️ {err}")
        return False, "Найдены критические дефекты в ссылках"

    print("✅ [Quality Gate] Все ссылки проверены живым запросом. Префлайт успешно пройден!")
    return True, "Готово к публикации"

if __name__ == "__main__":
    import os
    draft_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "draft_post.txt")
    if not os.path.exists(draft_file):
        print("Файл draft_post.txt не найден.")
        sys.exit(1)
    with open(draft_file, "r", encoding="utf-8") as f:
        ok, msg = inspect_draft(f.read())
    sys.exit(0 if ok else 1)
