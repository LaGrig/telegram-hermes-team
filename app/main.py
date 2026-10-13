import os
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
catalog_path = os.path.join(BASE_DIR, "catalog_perks.json")
html_path = os.path.join(BASE_DIR, "app", "index.html")

app = FastAPI(title="Hermes Mini App")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    if not os.path.exists(html_path):
        return "<h1>Файл index.html еще не создан. Спокойно, мы в процессе!</h1>"
    
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/catalog")
async def get_catalog():
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"error": "Ошибка чтения каталога"}
    return {"error": "Каталог пуст"}
