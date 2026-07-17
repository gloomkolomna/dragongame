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
ACCESS_TOKEN_EXPIRE_MINUTES = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 43200)
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
DONOR_SYNC_INTERVAL_HOURS = _env_int("DONOR_SYNC_INTERVAL_HOURS", 8)
REWARD_CHECK_INTERVAL_HOURS = _env_int("REWARD_CHECK_INTERVAL_HOURS", 24)

# ── Robokassa ──
ROBOKASSA_MERCHANT_LOGIN = os.getenv("ROBOKASSA_MERCHANT_LOGIN", "")
ROBOKASSA_PASSWORD1 = os.getenv("ROBOKASSA_PASSWORD1", "")
ROBOKASSA_PASSWORD2 = os.getenv("ROBOKASSA_PASSWORD2", "")
ROBOKASSA_TEST_PASSWORD1 = os.getenv("ROBOKASSA_TEST_PASSWORD1", "")
ROBOKASSA_TEST_PASSWORD2 = os.getenv("ROBOKASSA_TEST_PASSWORD2", "")
ROBOKASSA_TEST_MODE = os.getenv("ROBOKASSA_TEST_MODE", "1")
SITE_URL = os.getenv("SITE_URL", "https://belovolovhome.ru/dragons")
VK_GROUP_URL = os.getenv("VK_GROUP_URL", "https://vk.ru/bestiaryofdragonlegends")


def robokassa_is_test() -> bool:
    return str(ROBOKASSA_TEST_MODE).strip() == "1"


def robokassa_password1() -> str:
    if robokassa_is_test():
        return ROBOKASSA_TEST_PASSWORD1 or ROBOKASSA_PASSWORD1
    return ROBOKASSA_PASSWORD1


def robokassa_password2() -> str:
    if robokassa_is_test():
        return ROBOKASSA_TEST_PASSWORD2 or ROBOKASSA_PASSWORD2
    return ROBOKASSA_PASSWORD2

API_ERROR_LOG = os.getenv("API_ERROR_LOG", "/var/log/dragons/api-error.log")

DEBUG_LOG_REQUESTS = os.getenv("DEBUG_LOG_REQUESTS", "").strip() == "1"
DEBUG_LOG_PATH = os.getenv("DEBUG_LOG_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_requests.log"))


def get_allowed_vk_ids() -> set[int]:
    raw = os.getenv("VK_ALLOWED_IDS", "")
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
