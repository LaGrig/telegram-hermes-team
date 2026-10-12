#!/bin/bash
cd /home/ubuntu/telegram-hermes-team

# Подтягиваем переменные окружения (.env или bashrc)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Активируем виртуальное окружение
if [ -f app/.venv/bin/activate ]; then
    source app/.venv/bin/activate
elif [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Запускаем переданную команду
python "$@"
