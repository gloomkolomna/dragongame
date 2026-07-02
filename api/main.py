import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from config import FRONTEND_URL
from db import init_db

init_db()

app = FastAPI(title="Dragons Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "https://vk.com", "https://id.vk.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.collection import router as collection_router

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(collection_router)

# Каталог изображений — корневой <repo>/images (туда же пишет services/dragon_service).
# Раздаём через /api/static/images/{rest:path} -> <repo>/images/{rest}.


IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images")


@app.get("/api/static/images/{rest:path}")
def serve_image(rest: str):
    filepath = os.path.normpath(os.path.join(IMAGES_DIR, rest))
    if os.path.isfile(filepath):
        return FileResponse(filepath)

    dirpart = os.path.dirname(filepath)
    namepart = os.path.basename(filepath)
    if os.path.isdir(dirpart):
        low = namepart.lower()
        for f in os.listdir(dirpart):
            if f.lower() == low:
                return FileResponse(os.path.join(dirpart, f))

    raise HTTPException(status_code=404)


@app.get("/api/")
def health():
    return {"status": "ok", "service": "dragons-api"}
