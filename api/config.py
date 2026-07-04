import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── Общие ──
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dragons.db")
APP_ENV = os.getenv("APP_ENV", "production").strip().lower()
DEV_LOGIN_ENABLED = APP_ENV == "dev"
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://belovolovhome.ru/dragons")

# ── VK OAuth (админка) ──
VK_CLIENT_ID = os.getenv("VK_CLIENT_ID", "")
VK_CLIENT_SECRET = os.getenv("VK_CLIENT_SECRET", "")
VK_REDIRECT_URI = os.getenv("VK_REDIRECT_URI", "")

# ── VK Mini App ──
VK_APP_ID = int(os.getenv("VK_APP_ID", "0"))
VK_APP_SECRET = os.getenv("VK_APP_SECRET", "")

# ── VK Bot ──
VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN", "")
VK_GROUP_ID = int(os.getenv("VK_GROUP_ID", "0"))

API_ERROR_LOG = os.getenv("API_ERROR_LOG", "/var/log/dragons/api-error.log")


def get_allowed_vk_ids() -> set[int]:
    raw = os.getenv("VK_ALLOWED_IDS", "")
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
