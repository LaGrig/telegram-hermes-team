# Инструкция по запуску Hermes

## 1. Клонирование репозитория
```bash
git clone https://github.com/LaGrig/telegram-hermes-team.git
cd telegram-hermes-team

#Создание виртуального окружения
sudo apt update
sudo apt install -y python3-venv
python3 -m venv venv
source venv/bin/activate

#Установка зависимостей
pip install -r requirements.txt

#Проверка конфигурации агентов
python skills/test_agents.py
##Ожидаемый результат — список агентов из agents/team.yaml.

#Запуск теста взаимодействия
python skills/run_team.py

#Ожидаемый результат:

#Writer Bot фильтрует текст

#Searcher Bot считает количество слов

#6. Документация
##Все описания агентов и skills находятся в docs/agents.md.

#Эта инструкция хранится в docs/README.md.

#7. GitHub Actions
##При каждом git push запускается CI (.github/workflows/ci.yml).

#CI проверяет синтаксис YAML и Python.

