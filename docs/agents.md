# Документация: агенты Hermes

## Общая структура
Репозиторий содержит описание команды Hermes:
- `agents/` — YAML‑файлы с конфигурацией агентов
- `skills/` — Python‑скрипты (навыки)
- `docs/` — документация
- `.github/workflows/` — CI‑проверки

## Список агентов
- **searcher_bot** — Поисковик  
  Skills: `count_words`

- **writer_bot** — Писатель  
  Skills: `filter_text`

- **editor_bot** — Редактор  
  Skills: (пока пусто)

- **designer_bot** — Оформитель  
  Skills: (пока пусто)

- **publisher_bot** — Публикатор  
  Skills: (пока пусто)

- **audience_bot** — Тестировщик / представитель аудитории  
  Skills: (пока пусто)

- **dev_bot** — Программист  
  Skills: (пока пусто)

## Skills
- `filter_text` — очистка текста (writer_bot)
- `count_words` — подсчёт слов (searcher_bot)

## Назначение
Каждый агент выполняет свою роль.  
Skills подключаются через YAML и реализуются в Python.  
Документация обновляется при добавлении новых агентов или skills.
