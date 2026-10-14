import json
import os
import re

def delete_item_from_catalog(target: str, catalog_path: str) -> tuple[bool, str]:
    if not target or not target.strip():
        return False, "Пустой запрос на удаление."
        
    if not os.path.exists(catalog_path):
        return False, "Файл каталога не найден. База пуста."
        
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, f"Ошибка чтения каталога: {e}"
        
    target_lower = target.lower()
    
    # Слова, которые скрипт должен игнорировать при поиске
    stop_words = {"пост", "новость", "акцию", "скидку", "удали", "удалить", "карточку", "про", "из", "каталога"}
    
    # Очищаем от знаков препинания и бьем на слова
    words = re.findall(r'\w+', target_lower)
    
    # Оставляем только значимые слова длиннее 2 символов
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    # На случай, если запрос состоял только из коротких или стоп-слов
    if not keywords:
        keywords = words 
        
    deleted_count = 0
    deleted_titles = []
    
    def is_match(item_dict):
        item_str = json.dumps(item_dict, ensure_ascii=False).lower()
        # Проверяем, что ВСЕ ключевые слова есть в тексте карточки
        return all(kw in item_str for kw in keywords)
        
    if isinstance(data, list):
        new_data = []
        for item in data:
            if is_match(item):
                deleted_count += 1
                deleted_titles.append(item.get('title', 'Без названия'))
            else:
                new_data.append(item)
        data = new_data
        
    elif isinstance(data, dict):
        for category, items in data.items():
            if isinstance(items, list):
                new_items = []
                for item in items:
                    if is_match(item):
                        deleted_count += 1
                        deleted_titles.append(item.get('title', 'Без названия'))
                    else:
                        new_items.append(item)
                data[category] = new_items
                
    if deleted_count > 0:
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        titles_str = ", ".join(deleted_titles)
        return True, f"Удалено карточек: {deleted_count}\n(<i>{titles_str}</i>)"
    else:
        kw_str = ", ".join(keywords)
        return False, f"Акция по словам [<b>{kw_str}</b>] не найдена. Попробуй написать одно самое редкое слово (например: Kulturpark)."
