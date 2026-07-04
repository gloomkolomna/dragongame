from datetime import datetime, timezone, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

MSK = timezone(timedelta(hours=3))


async def log_failed_requests(request: Request, call_next):
    response = await call_next(request)
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
