import os, sys, json, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import httpx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from skills.editor import chat_with_editor

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
EDITOR_CHAT_ID = os.getenv("TELEGRAM_EDITOR_CHAT_ID")
CATALOG_FILE = os.path.join(BASE_DIR, "catalog_perks.json")

async def send_message(chat_id: int, text: str, reply_markup: dict = None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup: payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client: await client.post(url, json=payload)

async def answer_callback(callback_query_id: str, text: str = ""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    async with httpx.AsyncClient() as client: await client.post(url, json={"callback_query_id": callback_query_id, "text": text})

@asynccontextmanager
async def lifespan(app: FastAPI):
    if WEBHOOK_URL:
        async with httpx.AsyncClient() as client:
            await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", json={"url": f"{WEBHOOK_URL}/webhook"})
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "app")), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(BASE_DIR, "app", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f: return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Index file not found</h1>", status_code=404)

@app.get("/api/catalog")
async def get_catalog():
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE, "r", encoding="utf-8") as f: return JSONResponse(content=json.load(f))
    return JSONResponse(content={})

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    
    if "callback_query" in update:
        cq = update["callback_query"]
        data = cq["data"]
        chat_id = cq["message"]["chat"]["id"]
        msg_id = cq["message"]["message_id"]
        
        if data == "CLEAR_REJECT_LOG":
            from skills.editor import clear_rejection_log
            clear_rejection_log()
            await send_message(chat_id, "✅ Лог мусора очищен. Начинаем собирать аналитику с чистого листа.")
            await answer_callback(cq["id"])
            await httpx.AsyncClient().post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup", json={"chat_id": chat_id, "message_id": msg_id, "reply_markup": {"inline_keyboard": []}})

        elif data in ["PUBLISH_DIGEST", "PUBLISH_TOP", "CANCEL"]:
            response_data = await chat_with_editor(data)
            await send_message(chat_id, response_data["text"])
            await answer_callback(cq["id"])
            
        elif data.startswith("ad_extend_") or data.startswith("ad_delete_"):
            action, item_id = data.split("_")[1], data.split("_", 2)[2]
            
            if os.path.exists(CATALOG_FILE):
                with open(CATALOG_FILE, "r", encoding="utf-8") as f: cat_data = json.load(f)
                
                for cat, items in cat_data.items():
                    for i, it in enumerate(items):
                        if it.get("id") == item_id:
                            if action == "delete":
                                items.pop(i)
                                await send_message(chat_id, f"🗑 Рекламный пост <b>{item_id}</b> удален.")
                            elif action == "extend":
                                from datetime import datetime, timedelta
                                it["ad_until"] = (datetime.now() + timedelta(days=1)).isoformat()
                                it["alert_sent"] = False
                                await send_message(chat_id, f"✅ Срок жизни поста продлен на 24 часа.")
                            break
                with open(CATALOG_FILE, "w", encoding="utf-8") as f: json.dump(cat_data, f, ensure_ascii=False, indent=2)
            await answer_callback(cq["id"])
            await httpx.AsyncClient().post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup", json={"chat_id": chat_id, "message_id": msg_id, "reply_markup": {"inline_keyboard": []}})

    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        if str(chat_id) == str(EDITOR_CHAT_ID):
            text = update["message"]["text"]
            
            # КОМАНДА ПЛАНЕРКИ
            if text == "/planerka":
                action_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"
                async with httpx.AsyncClient() as client: await client.post(action_url, json={"chat_id": chat_id, "action": "typing"})
                
                from skills.editor import generate_rejection_report
                response_data = await generate_rejection_report()
                kb = {"inline_keyboard": [[{"text": bt, "callback_data": cb} for bt, cb in response_data["buttons"]]]} if response_data.get("buttons") else None
                await send_message(chat_id, response_data["text"], reply_markup=kb)
                return {"ok": True}
                
            if text == "/start":
                await send_message(chat_id, "Привет, Шеф! Кидай ссылки на акции или пиши /planerka для анализа мусора.")
                return {"ok": True}
                
            # Обычный чат
            action_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction"
            async with httpx.AsyncClient() as client: await client.post(action_url, json={"chat_id": chat_id, "action": "typing"})
            
            response_data = await chat_with_editor(text)
            kb = {"inline_keyboard": [[{"text": bt, "callback_data": cb} for bt, cb in response_data["buttons"]]]} if response_data.get("buttons") else None
            await send_message(chat_id, response_data["text"], reply_markup=kb)
            
    return {"ok": True}
