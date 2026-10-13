# 📘 Hermes Student Telegram Platform: Полная техническая спецификация и руководство по развертыванию с нуля (Disaster Recovery Blueprint)

Этот документ содержит исчерпывающее описание архитектуры, ролевой модели ИИ-агентов, внешних интеграций, необходимых секретов, исходного содержимого ключевых конфигурационных файлов и пошагового алгоритма развертывания проекта с абсолютного нуля на чистом сервере Ubuntu (ARM64 / x86_64).

---

## 1. Обзор проекта и общая архитектура

Платформа представляет собой автономный редакционный цикл для студенческого Telegram-канала и интерактивного Telegram Mini App.

### Схема взаимодействия компонентов

```text
[Внешние источники: RSS / Студпорталы / Web Search]
                    │
                    ▼
       [1. skills/local_scraper.py]
                    │
                    ▼ (сырые данные)
       [2. skills/editorial.py + llm_worker.py] ◄── [OpenRouter API / LLM]
                    │
                    ▼ (валидация, отбор, форматирование)
         [catalog_perks.json] ───────────────┐
                    │                        │ (база данных)
                    ▼                        ▼
       [3. skills/publisher.py]      [4. app/main.py (FastAPI :8000)]
                    │                        │
                    ▼                        ▼
         [Telegram Channel]       [Cloudflare Zero Trust Tunnel]
     (Пост с WebApp кнопкой)                 │
                    ▲                        ▼
                    └─────────── [Telegram Mini App: app/index.html]
```

### Регулярные автономные циклы (Cron):
1. **03:00** — ночной аудит ссылок и удаление устаревших/недействительных постов (`skills/cleaner.py`).
2. **08:30** — утренний сбор предложений и отправка черновика в закрытый чат Главреда (`cron_morning.py`).
3. **17:00** — полный конвейер: парсинг, ИИ-оценка, обновление каталога и публикация вечернего поста с инлайн-кнопкой Mini App (`run_pipeline.py --publish`).

---

## 2. Ролевая модель и зоны ответственности

| Роль / Модуль | Файл | Описание задачи |
|---|---|---|
| **Скрапер (Data Ingestion)** | `skills/local_scraper.py` | Мониторит RSS-ленты словацких студенческих ресурсов, сайты университетов, агрегаторы вакансий и скидок ISIC. |
| **ИИ-Редактор (Editorial AI)** | `skills/editorial.py` | Анализирует входящий поток данных, отсеивает спам/нерелевантные офферы, проверяет студенческую ценность и формирует саммари. |
| **LLM-Воркер (AI Client)** | `skills/llm_worker.py` | Управляет вызовами языковой модели через OpenRouter API (температура, промпты, формат JSON). |
| **Очередь обработки (Agent Consumer)** | `skills/agent_consumer.py` | Обрабатывает пакетные запросы к нейросети и управляет повторными попытками при сбоях API. |
| **Публикатор (Publisher)** | `skills/publisher.py` | Формирует разметку поста (HTML/Markdown) и отправляет его в Telegram-канал с инлайн-кнопкой `InlineKeyboardButton(text=..., web_app=WebAppInfo(url=...))`. |
| **Санитар (Cleaner)** | `skills/cleaner.py` | Проверяет статус внешних ссылок (HTTP 200 vs 404), архивирует сгоревшие акции в JSON и удаляет неактуальные посты из канала. |
| **Утренний Ассистент** | `cron_morning.py` | Формирует сводку кандидатов за последние сутки и присылает отчёт в личный чат Главреда. |
| **Бэкенд Mini App** | `app/main.py` | Сервер FastAPI: отдает статический SPA `index.html` и JSON-эндпоинт `/api/perks` для динамической фильтрации. |
| **Фронтенд Mini App** | `app/index.html` | Одностраничное приложение (SPA) на чистом JS/CSS: подключает Telegram WebApp JS SDK, поддерживает темную/светлую тему, мгновенный поиск и фильтрацию по категориям. |

---

## 3. Внешние подключения, токены и API-ключи

Для работы платформы требуются 5 внешних сервисов:

### 3.1. Telegram Bot (@BotFather)
1. Открыть `@BotFather` в Telegram, отправить `/newbot`.
2. Задать имя (например, `Hermes Student Assistant`) и юзернейм (например, `studperks_bot`).
3. Получить **HTTP API Token** вида `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`.
4. Создать Mini App:
   - В `@BotFather` отправить `/newapp`.
   - Выбрать созданного бота.
   - Указать заголовок (`Каталог Hermes`) и описание.
   - Загрузить аватарку $640 \times 640$ px.
   - В поле **Web App URL** указать постоянный HTTPS-домен туннеля (например, `https://app.yourdomain.com`).
   - Задать короткое имя (`Short Name`, например `discounts_catalog`).
   - Получить ссылку вида `t.me/studperks_bot/discounts_catalog`.

### 3.2. Telegram-канал и чат Главреда
1. Создать публичный или приватный канал (например, `@hermes_students`).
2. Добавить созданного бота в **Администраторы канала** с правами:
   - *Post Messages* (Публикация сообщений);
   - *Edit Messages* (Редактирование сообщений);
   - *Delete Messages* (Удаление сообщений).
3. Узнать свой персональный `TELEGRAM_EDITOR_CHAT_ID` (написать боту `@userinfobot` или `@getmyid_bot`).

### 3.3. LLM API (OpenRouter)
1. Зарегистрироваться на [openrouter.ai](https://openrouter.ai).
2. Перейти в раздел **Keys** $\rightarrow$ **Create Key** и сохранить полученный токен `sk-or-v1-...`.
3. Модель по умолчанию: `qwen/qwen-2.5-72b-instruct` или `meta-llama/llama-3.3-70b-instruct` (оптимальное соотношение цены, интеллекта и скорости).

### 3.4. Cloudflare Zero Trust (Туннель)
1. Добавить свой домен (например, `yourdomain.com`) в Cloudflare.
2. Перейти в [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) $\rightarrow$ **Networks** $\rightarrow$ **Tunnels** $\rightarrow$ **Add a tunnel**.
3. Тип: **Cloudflared** $\rightarrow$ ввести имя туннеля $\rightarrow$ сохранить.
4. Выбрать ОС `Debian ARM64` и скопировать установочный токен службы (`sudo cloudflared service install <TOKEN>`).
5. В разделе **Public Hostname**:
   - Subdomain: `app` (или `catalog`);
   - Domain: `yourdomain.com`;
   - Type: `HTTP`;
   - URL: `localhost:8000`.

### 3.5. GitHub Репозиторий
- URL репозитория: `https://github.com/LaGrig/telegram-hermes-team.git`
- На сервере настраивается SSH-ключ (`ssh-keygen -t ed25519`) или Personal Access Token (PAT) для выполнения `git pull` и `git push`.

---

## 4. Эталонные файлы проекта

### 4.1. Файл переменных окружения `.env` (Шаблон)
Файл располагается в корне проекта (`/home/ubuntu/telegram-hermes-team/.env`):

```ini
# ==============================================
# TELEGRAM CREDENTIALS
# ==============================================
TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHANNEL_ID="@hermes_students"
TELEGRAM_EDITOR_CHAT_ID="123456789"

# ==============================================
# TELEGRAM MINI APP
# ==============================================
MINI_APP_URL="https://app.yourdomain.com"
MINI_APP_SHORT_NAME="discounts_catalog"

# ==============================================
# LLM CONFIGURATION (OPENROUTER)
# ==============================================
OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
LLM_BASE_URL="https://openrouter.ai/api/v1"
LLM_MODEL="qwen/qwen-2.5-72b-instruct"

# ==============================================
# FASTAPI BACKEND CONFIG
# ==============================================
APP_HOST="127.0.0.1"
APP_PORT=8000
```

---

### 4.2. Файл зависимостей `requirements.txt`
```text
pyyaml>=6.0.1
requests>=2.31.0
feedparser>=6.0.10
duckduckgo-search>=8.1.1
beautifulsoup4>=4.12.3
fastapi>=0.110.0
uvicorn>=0.28.0
lxml>=5.3.0
```

---

### 4.3. Файл игнорирования Git `.gitignore`
```text
venv/
.venv
*.deb
*.log
evaluated_cache.json
raw_candidates.json
.env
__pycache__/
*.pyc
.DS_Store
```

---

### 4.4. Скрипт-обертка запуска Cron `run_cron.sh`
Файл `/home/ubuntu/telegram-hermes-team/run_cron.sh` (права `chmod +x`):

```bash
#!/bin/bash
set -e
cd /home/ubuntu/telegram-hermes-team

# Подтягиваем переменные окружения
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Активируем виртуальное окружение
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

# Запуск переданной команды
python "$@"
```

---

### 4.5. Системный сервис `fastapi.service`
Файл `/etc/systemd/system/fastapi.service`:

```ini
[Unit]
Description=Hermes Team Telegram Mini App FastAPI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-hermes-team
ExecStart=/home/ubuntu/telegram-hermes-team/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/telegram-hermes-team/.env

[Install]
WantedBy=multi-user.target
```

---

### 4.6. Бэкенд Mini App `app/main.py`
```python
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent
CATALOG_PATH = BASE_DIR / "catalog_perks.json"
INDEX_HTML_PATH = BASE_DIR / "app" / "index.html"

app = FastAPI(title="Hermes Perks Catalog API")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if not INDEX_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    return INDEX_HTML_PATH.read_text(encoding="utf-8")

@app.get("/api/perks")
async def get_perks():
    if not CATALOG_PATH.exists():
        return JSONResponse(content={"perks": []})
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading catalog: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "hermes-mini-app"}
```

---

### 4.7. Фронтенд Mini App `app/index.html`
```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Каталог студенческих скидок Hermes</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    :root {
      --bg: var(--tg-theme-bg-color, #ffffff);
      --text: var(--tg-theme-text-color, #1a1a1a);
      --hint: var(--tg-theme-hint-color, #8e8e93);
      --link: var(--tg-theme-link-color, #2481cc);
      --button: var(--tg-theme-button-color, #2481cc);
      --button-text: var(--tg-theme-button-text-color, #ffffff);
      --secondary-bg: var(--tg-theme-secondary-bg-color, #f2f2f7);
      --card-bg: var(--tg-theme-bg-color, #ffffff);
    }
    body {
      margin: 0;
      padding: 12px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: var(--secondary-bg);
      color: var(--text);
      -webkit-font-smoothing: antialiased;
    }
    header {
      margin-bottom: 12px;
    }
    h1 {
      font-size: 20px;
      margin: 0 0 6px 0;
      font-weight: 700;
    }
    p.subtitle {
      margin: 0;
      font-size: 13px;
      color: var(--hint);
    }
    .search-box {
      width: 100%;
      box-sizing: border-box;
      padding: 10px 14px;
      border-radius: 10px;
      border: 1px solid rgba(0,0,0,0.1);
      background: var(--bg);
      color: var(--text);
      font-size: 15px;
      margin-bottom: 10px;
      outline: none;
    }
    .categories {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 8px;
      margin-bottom: 8px;
    }
    .pill {
      white-space: nowrap;
      padding: 6px 12px;
      border-radius: 16px;
      background: var(--bg);
      border: 1px solid rgba(0,0,0,0.08);
      font-size: 12px;
      cursor: pointer;
      font-weight: 500;
    }
    .pill.active {
      background: var(--button);
      color: var(--button-text);
      border-color: var(--button);
    }
    .grid {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .card {
      background: var(--card-bg);
      border-radius: 12px;
      padding: 14px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      border: 1px solid rgba(0,0,0,0.04);
    }
    .card-title {
      font-size: 16px;
      font-weight: 600;
      margin: 0 0 6px 0;
    }
    .card-badge {
      display: inline-block;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 6px;
      background: var(--secondary-bg);
      color: var(--hint);
      margin-bottom: 8px;
      font-weight: 600;
    }
    .card-desc {
      font-size: 13px;
      line-height: 1.4;
      margin: 0 0 10px 0;
      color: var(--text);
    }
    .card-link {
      display: inline-block;
      text-decoration: none;
      font-size: 13px;
      color: var(--link);
      font-weight: 600;
    }
  </style>
</head>
<body>
  <header>
    <h1>Студенческий каталог Hermes</h1>
    <p class="subtitle">Скидки, стажировки и бонусы в Словакии</p>
  </header>

  <input type="text" id="searchInput" class="search-box" placeholder="Поиск акций, заведений, вакансий...">

  <div class="categories" id="categories">
    <div class="pill active" data-cat="all">Все</div>
    <div class="pill" data-cat="food">Еда</div>
    <div class="pill" data-cat="transport">Транспорт</div>
    <div class="pill" data-cat="it">IT & Обучение</div>
    <div class="pill" data-cat="leisure">Досуг</div>
  </div>

  <div class="grid" id="perksList">
    <p style="text-align: center; color: var(--hint); font-size: 14px;">Загрузка актуальных акций...</p>
  </div>

  <script>
    const tg = window.Telegram ? window.Telegram.WebApp : null;
    if (tg) {
      tg.expand();
      tg.ready();
    }

    let allPerks = [];
    let currentCategory = 'all';

    async function fetchPerks() {
      try {
        const res = await fetch('/api/perks');
        const data = await res.json();
        allPerks = Array.isArray(data) ? data : (data.perks || []);
        render();
      } catch (err) {
        document.getElementById('perksList').innerHTML = '<p style="text-align:center;color:red;font-size:14px;">Ошибка загрузки каталога</p>';
      }
    }

    function render() {
      const query = document.getElementById('searchInput').value.toLowerCase().trim();
      const list = document.getElementById('perksList');

      const filtered = allPerks.filter(item => {
        const matchesCat = currentCategory === 'all' || (item.category && item.category.toLowerCase() === currentCategory);
        const matchesQuery = !query || 
          (item.title && item.title.toLowerCase().includes(query)) ||
          (item.description && item.description.toLowerCase().includes(query));
        return matchesCat && matchesQuery;
      });

      if (filtered.length === 0) {
        list.innerHTML = '<p style="text-align: center; color: var(--hint); font-size: 14px;">Ничего не найдено</p>';
        return;
      }

      list.innerHTML = filtered.map(item => `
        <div class="card">
          <span class="card-badge">${item.category ? item.category.toUpperCase() : 'АКЦИЯ'}</span>
          <div class="card-title">${item.title || 'Предложение'}</div>
          <div class="card-desc">${item.description || ''}</div>
          ${item.link ? `<a class="card-link" href="${item.link}" target="_blank">Подробнее ↗</a>` : ''}
        </div>
      `).join('');
    }

    document.getElementById('searchInput').addEventListener('input', render);

    document.querySelectorAll('.pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        currentCategory = pill.dataset.cat;
        render();
      });
    });

    fetchPerks();
  </script>
</body>
</html>
```

---

## 5. Пошаговая инструкция развертывания с нуля на чистом сервере

### Шаг 1. Первоначальная настройка ОС Ubuntu

Выполняется под пользователем `ubuntu`:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git curl ufw
```

### Шаг 2. Клонирование репозитория

```bash
cd /home/ubuntu
git clone https://github.com/LaGrig/telegram-hermes-team.git
cd /home/ubuntu/telegram-hermes-team
```

### Шаг 3. Изолированное окружение Python и симлинк

Создаем чистое рабочее окружение `venv` и символическую ссылку `.venv`:

```bash
python3 -m venv venv
ln -s /home/ubuntu/telegram-hermes-team/venv /home/ubuntu/telegram-hermes-team/.venv
```

Устанавливаем зависимости:
```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 4. Создание файла `.env` с секретами

```bash
cat << 'EOF' > /home/ubuntu/telegram-hermes-team/.env
TELEGRAM_BOT_TOKEN="ТВОЙ_ТОКЕН_БОТА"
TELEGRAM_CHANNEL_ID="@ТВОЙ_КАНАЛ"
TELEGRAM_EDITOR_CHAT_ID="ТВОЙ_CHAT_ID"
MINI_APP_URL="https://app.yourdomain.com"
MINI_APP_SHORT_NAME="discounts_catalog"
OPENROUTER_API_KEY="sk-or-v1-ТВОЙ_КЛЮЧ"
LLM_BASE_URL="https://openrouter.ai/api/v1"
LLM_MODEL="qwen/qwen-2.5-72b-instruct"
APP_HOST="127.0.0.1"
APP_PORT=8000
EOF

chmod 600 /home/ubuntu/telegram-hermes-team/.env
```

### Шаг 5. Настройка системной службы FastAPI в systemd

Создаем юнит `/etc/systemd/system/fastapi.service`:

```bash
sudo bash -c 'cat << "EOF" > /etc/systemd/system/fastapi.service
[Unit]
Description=Hermes Team Telegram Mini App FastAPI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-hermes-team
ExecStart=/home/ubuntu/telegram-hermes-team/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/telegram-hermes-team/.env

[Install]
WantedBy=multi-user.target
EOF'
```

Активируем и запускаем службу:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi
```

### Шаг 6. Установка и запуск Cloudflare Zero Trust Tunnel

1. Скачиваем deb-пакет для ARM64:
```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared.deb
rm -f cloudflared.deb
```

2. Устанавливаем постоянную системную службу токеном из панели Cloudflare:
```bash
sudo cloudflared service install <ТОКЕН_ИЗ_ПАНЕЛИ_CLOUDFLARE_ZERO_TRUST>
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

3. В веб-панели Cloudflare (Zero Trust $\rightarrow$ Tunnels $\rightarrow$ твой туннель $\rightarrow$ Public Hostnames) прописываем маршрут:
   - **Hostname**: `app.yourdomain.com`
   - **Service**: `HTTP` $\rightarrow$ `localhost:8000`

### Шаг 7. Права на скрипты и планировщик Cron

Даем права на выполнение скрипта:
```bash
chmod +x /home/ubuntu/telegram-hermes-team/run_cron.sh
```

Устанавливаем расписание:
```bash
(crontab -l 2>/dev/null; echo "# Hermes Autonomous Pipeline Schedule"; \
echo "0 3 * * * /home/ubuntu/telegram-hermes-team/run_cron.sh skills/cleaner.py audit >> /home/ubuntu/telegram-hermes-team/cleaner.log 2>&1"; \
echo "30 8 * * * /home/ubuntu/telegram-hermes-team/run_cron.sh cron_morning.py >> /home/ubuntu/telegram-hermes-team/morning.log 2>&1"; \
echo "0 17 * * * cd /home/ubuntu/telegram-hermes-team && /home/ubuntu/telegram-hermes-team/venv/bin/python run_pipeline.py --publish >> /home/ubuntu/telegram-hermes-team/cron.log 2>&1") | crontab -
```

---

## 6. Чек-лист проверки и верификации (Post-Deploy Checklist)

Выполни проверочный скрипт после завершения настройки:

```bash
echo "=== 1. Проверка FastAPI службы ===" && systemctl is-active fastapi
echo "=== 2. Проверка Cloudflare Tunnel ===" && systemctl is-active cloudflared
echo "=== 3. Проверка Cron службы ===" && systemctl is-active cron
echo "=== 4. Проверка локального порта 8000 ===" && curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/
echo "=== 5. Проверка симлинка окружения ===" && ls -l /home/ubuntu/telegram-hermes-team/.venv
echo "=== 6. Проверка задач cron ===" && crontab -l | grep -v '^#'
```

**Ожидаемый вывод:**
- Службы `fastapi`, `cloudflared`, `cron` выводят `active`.
- Порт 8000 возвращает `HTTP Status: 200`.
- Симлинк указывает на `venv`.
- В crontab присутствуют три задачи (03:00, 08:30, 17:00).

---

## 7. Ручной запуск и тестирование конвейера

Чтобы протестировать полный цикл генерации контента и публикации поста в Telegram:

```bash
cd /home/ubuntu/telegram-hermes-team
source venv/bin/activate
python run_pipeline.py --publish
```

После выполнения:
1. В целевом Telegram-канале должен появиться пост с подборкой актуальных офферов.
2. Под постом должна присутствовать инлайн-кнопка открытия Mini App.
3. При нажатии на кнопку приложение должно открыться в интерфейсе Telegram и отобразить актуальные карточки из `catalog_perks.json`.