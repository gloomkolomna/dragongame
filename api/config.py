import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "")
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError):
        return default

# ── Общие ──
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 480)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dragons.db")
APP_ENV = os.getenv("APP_ENV", "production").strip().lower()
DEV_LOGIN_ENABLED = APP_ENV == "dev"
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://belovolovhome.ru/dragons")

# ── VK OAuth (админка) ──
VK_CLIENT_ID = os.getenv("VK_CLIENT_ID", "")
VK_CLIENT_SECRET = os.getenv("VK_CLIENT_SECRET", "")
VK_REDIRECT_URI = os.getenv("VK_REDIRECT_URI", "")

# ── VK Mini App ──
VK_APP_ID = _env_int("VK_APP_ID", 0)
VK_APP_SECRET = os.getenv("VK_APP_SECRET", "")

# ── VK Bot ──
VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN", "")
VK_GROUP_ID = _env_int("VK_GROUP_ID", 0)
ADMIN_VK_ID = _env_int("ADMIN_VK_ID", 0)

# ── Анти-чит ──
ANTI_CHEAT_MULTIPLIER = _env_int("ANTI_CHEAT_MULTIPLIER", 5)

# ── Донат (VK Donut) ──
DONUT_API_URL = os.getenv("DONUT_API_URL", "").rstrip("/")
DONUT_API_KEY = os.getenv("DONUT_API_KEY", "")
DONOR_SYNC_INTERVAL_HOURS = _env_int("DONOR_SYNC_INTERVAL_HOURS", 24)

API_ERROR_LOG = os.getenv("API_ERROR_LOG", "/var/log/dragons/api-error.log")


def get_allowed_vk_ids() -> set[int]:
    raw = os.getenv("VK_ALLOWED_IDS", "")
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
