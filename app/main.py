import os
import sys
import json
import httpx
import asyncio
import subprocess
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv

from skills.router import analyze_intent
from skills.scraper import run_smart_scraper
from skills.editor import rewrite_post
from skills.moderator import delete_item_from_catalog
# ПОДКЛЮЧАЕМ СНАЙПЕРА (он асинхронный)
import importlib.util

def load_sniper():
    sniper_path = os.path.join(os.path.dirname(__file__), "..", "skills", "sniper.py")
    if os.path.exists(sniper_path):
        spec = importlib.util.spec_from_file_location("sniper", sniper_path)
        sniper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sniper)
        return sniper
    return None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
EDITOR_CHAT_ID = os.getenv("TELEGRAM_EDITOR_CHAT_ID")
PUBLIC_CHANNEL_ID = os.getenv("TELEGRAM_CHAT_ID")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://t.me/HermesKosiceBot/app")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

CATALOG_FILE = os.path.join(BASE_DIR, "catalog_perks.json")
DRAFT_FILE = os.path.join(BASE_DIR, "draft_post.txt")
CANCEL_FLAG = os.path.join(BASE_DIR, "cancel_publish.flag")

app = FastAPI(title="Hermes Team")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Index file not found</h1>", status_code=404)

@app.get("/api/catalog")
async def get_catalog():
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)
    return JSONResponse(content=[])

async def send_telegram_message(chat_id: str, text: str, reply_markup: dict = None, parse_mode: str = "HTML"):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "disable_web_page_preview": True
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload)
            if res.status_code != 200 and parse_mode:
                payload.pop("parse_mode", None)
                await client.post(url, json=payload)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

async def edit_telegram_message(chat_id: str, message_id: int, text: str):
    url = f"{TELEGRAM_API_URL}/editMessageText"
    payload = {
        "chat_id": chat_id, 
        "message_id": message_id,
        "text": text, 
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": []}
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def answer_callback_query(callback_query_id: str, text: str):
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id, "text": text}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def execute_action(chat_id: str, action: str, params: dict, is_digest_edit: bool = False):
    if action == "run_scraper":
        topic = params.get("topic", "без темы")
        await send_telegram_message(chat_id, f"⏳ Ищейка ушла в сеть искать: <b>{topic}</b>...")
        real_result = await run_smart_scraper(topic)
        await send_telegram_message(chat_id, real_result, parse_mode=None)

    elif action == "sniper_publish":
        # СНАЙПЕР В ДЕЛЕ
        await send_telegram_message(chat_id, "🔭 <i>Снайпер залег на крыше и сканирует раздачи ключей...</i>")
        sniper_module = load_sniper()
        if sniper_module and hasattr(sniper_module, "run_sniper"):
            result = await asyncio.get_event_loop().run_in_executor(None, sniper_module.run_sniper)
            
            # Если снайпер что-то нашел, даем кнопку "В канал"
            if "ШАРА" in result:
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🔥 Пульнуть в канал", "callback_data": "pub_channel"}],
                        [{"text": "❌ Отбой", "callback_data": "reject_post"}]
                    ]
                }
                await send_telegram_message(chat_id, result, reply_markup=keyboard)
            else:
                await send_telegram_message(chat_id, result)
        else:
            await send_telegram_message(chat_id, "❌ Модуль снайпера не найден.")

    elif action == "rewrite_draft":
        original_text = params.get("text", "")
        instructions = params.get("instructions", "Сделай классный пост")
        
        await send_telegram_message(chat_id, f"✍️ Редактор вносит правки: <i>{instructions}</i>...")
        real_rewritten = await rewrite_post(original_text, instructions)
        
        if is_digest_edit:
            with open(DRAFT_FILE, "w", encoding="utf-8") as f:
                f.write(real_rewritten)
            header = "✅ <b>Черновик Дайджеста на 17:00 обновлен!</b>\n────────────────────\n\n"
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🚀 Опубликовать прямо сейчас", "callback_data": "publish_digest_now"}],
                    [{"text": "🛑 Отменить автопостинг в 17:00", "callback_data": "cancel_autopublish"}]
                ]
            }
            await send_telegram_message(chat_id, header + real_rewritten, reply_markup=keyboard)
        else:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔥 ШАРА (В канал)", "callback_data": "pub_channel"}],
                    [{"text": "📝 Сделать черновиком Дайджеста", "callback_data": "pub_digest"}],
                    [{"text": "🔄 Отклонить", "callback_data": "reject_post"}]
                ]
            }
            await send_telegram_message(chat_id, real_rewritten, reply_markup=keyboard)

    elif action == "delete_perk":
        target = params.get("target", "")
        await send_telegram_message(chat_id, f"🔍 Ищу «<b>{target}</b>» в каталоге для удаления...")
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, delete_item_from_catalog, target, CATALOG_FILE)
        if success:
            await send_telegram_message(chat_id, f"🗑 <b>Успешно удалено!</b>\n{msg}")
        else:
            await send_telegram_message(chat_id, f"⚠️ <b>Результат:</b>\n{msg}")

    elif action == "chat":
        pass

@app.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        update = await request.json()
        
        if "callback_query" in update:
            callback = update["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            data = callback["data"]
            callback_id = callback["id"]
            post_text = callback["message"].get("text", "") 
            
            if data == "publish_digest_now":
                subprocess.run([sys.executable, os.path.join(BASE_DIR, "skills/publisher.py")], cwd=BASE_DIR)
                with open(CANCEL_FLAG, "w") as f:
                    f.write("published_early")
                background_tasks.add_task(edit_telegram_message, chat_id, message_id, post_text + "\n\n(🚀 ОПУБЛИКОВАНО ДОСРОЧНО)")
                background_tasks.add_task(answer_callback_query, callback_id, "Дайджест опубликован!")

            elif data == "cancel_autopublish":
                with open(CANCEL_FLAG, "w") as f:
                    f.write("cancelled")
                background_tasks.add_task(edit_telegram_message, chat_id, message_id, post_text + "\n\n(🛑 АВТОПУБЛИКАЦИЯ ОТМЕНЕНА)")
                background_tasks.add_task(answer_callback_query, callback_id, "Отменено!")

            elif data == "pub_channel":
                app_btn = {"inline_keyboard": [[{"text": "📱 Открыть полный каталог", "url": MINI_APP_URL}]]}
                background_tasks.add_task(edit_telegram_message, chat_id, message_id, post_text + "\n\n(🔥 ШАРА УЛЕТЕЛА В КАНАЛ)")
                background_tasks.add_task(answer_callback_query, callback_id, "Улетело в канал!")
                background_tasks.add_task(send_telegram_message, PUBLIC_CHANNEL_ID, post_text, app_btn)
                
            elif data == "pub_digest":
                with open(DRAFT_FILE, "w", encoding="utf-8") as f:
                    f.write(post_text)
                background_tasks.add_task(edit_telegram_message, chat_id, message_id, post_text + "\n\n(📝 СОХРАНЕНО В ЧЕРНОВИК)")
                background_tasks.add_task(answer_callback_query, callback_id, "Обновлено!")
                
            elif data == "reject_post":
                background_tasks.add_task(edit_telegram_message, chat_id, message_id, post_text + "\n\n(❌ ОТКЛОНЕНО)")
                background_tasks.add_task(answer_callback_query, callback_id, "Отклонено")
                
            return JSONResponse(content={"status": "ok"})
            
        elif "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text") or message.get("caption") or ""
            
            reply_to = message.get("reply_to_message")
            is_digest_edit = False
            
            if reply_to:
                original_text = reply_to.get("text") or reply_to.get("caption") or ""
                if "ВЕЧЕРНИЙ ДАЙДЖЕСТ" in original_text or "ПРЕВЬЮ ДАЙДЖЕСТА" in original_text:
                    is_digest_edit = True
                    if os.path.exists(DRAFT_FILE):
                        with open(DRAFT_FILE, "r", encoding="utf-8") as f:
                            original_text = f.read()
                if original_text:
                    text = f"[ИСХОДНЫЙ ТЕКСТ]:\n{original_text}\n\n[ЗАДАЧА]:\n{text}"
            
            if str(chat_id) == str(EDITOR_CHAT_ID) and text:
                intent = await analyze_intent(text)
                action = intent.get("action", "chat")
                params = intent.get("params", {})
                reply_text = intent.get("reply", "Принято.")
                
                background_tasks.add_task(send_telegram_message, chat_id, reply_text)
                background_tasks.add_task(execute_action, chat_id, action, params, is_digest_edit)
                
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        return JSONResponse(content={"status": "ok", "error": str(e)})
