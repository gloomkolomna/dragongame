import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

images_path = os.path.join(os.path.dirname(__file__), "..", "images")
if os.path.isdir(images_path):
    app.mount("/api/static/images", StaticFiles(directory=images_path), name="images")


@app.get("/api/")
def health():
    return {"status": "ok", "service": "dragons-api"}
