import os
import json
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")
USERS_FILE = "users.json"

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(
        text="🔥 Выбрать скидки",
        web_app=WebAppInfo(url=WEBAPP_URL)
    ))
    await msg.answer("Привет! Нажми кнопку ниже, чтобы выбрать, какие промокоды и скидки тебе присылать:", reply_markup=kb)

@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def webapp_data(msg: types.Message):
    data = msg.web_app_data.data
    try:
        parsed = json.loads(data)
        category = parsed.get("category", "unknown")
    except Exception:
        category = data

    user_id = str(msg.from_user.id)
    
    # Загружаем существующую базу пользователей
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            try:
                users = json.load(f)
            except json.JSONDecodeError:
                pass

    # Обновляем категорию для текущего студента
    users[user_id] = category

    # Сохраняем обратно в файл
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    await msg.answer(f"✅ Настроено! Теперь ты будешь получать скидки из раздела: <b>{category}</b>", parse_mode="HTML")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
