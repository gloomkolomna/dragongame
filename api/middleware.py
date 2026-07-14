import os
import json
from datetime import datetime, timezone, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

MSK = timezone(timedelta(hours=3))

_DEBUG_ENABLED: bool | None = None
_DEBUG_PATH: str | None = None


def _ensure_debug():
    global _DEBUG_ENABLED, _DEBUG_PATH
    if _DEBUG_ENABLED is None:
        _DEBUG_ENABLED = os.getenv("DEBUG_LOG_REQUESTS", "").strip() == "1"
        _DEBUG_PATH = os.getenv("DEBUG_LOG_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_requests.log")


async def log_failed_requests(request: Request, call_next):
    _ensure_debug()
    response = await call_next(request)
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    ua = request.headers.get("user-agent", "")[:200]

    if _DEBUG_ENABLED:
        entry = {
            "ts": datetime.now(MSK).isoformat(),
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
            "origin": origin,
            "referer": referer,
            "ua": ua,
            "ip": request.client.host if request.client else "",
        }
        try:
            with open(_DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    if response.status_code >= 400:
        try:
            from db import SessionLocal
            from models import ApiRequestLog
            db = SessionLocal()
            entry = ApiRequestLog(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                client_ip=request.client.host if request.client else "",
                created_at=datetime.now(MSK).isoformat(),
            )
            db.add(entry)
            db.commit()
            db.close()
        except Exception:
            pass
    return response
