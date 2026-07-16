import secrets
import hashlib
import base64
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
from db import get_db
from models import User
from config import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    VK_CLIENT_ID, VK_CLIENT_SECRET, VK_REDIRECT_URI,
    VK_APP_SECRET,
    get_allowed_vk_ids,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

VK_ID_AUTH_URL = "https://id.vk.ru/authorize"
VK_ID_TOKEN_URL = "https://id.vk.ru/oauth2/auth"
VK_ID_USER_INFO_URL = "https://id.vk.ru/oauth2/user_info"

STATE_COOKIE = "vk_oauth_state"
CODE_VERIFIER_COOKIE = "vk_code_verifier"
COOKIE_TTL = 600


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: Optional[str] = None


def get_user(db: Session, vk_id: str):
    return db.query(User).filter(User.vk_id == vk_id).first()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def compute_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_device_id() -> str:
    return secrets.token_hex(16)


def get_vk_login_url(state: str, code_challenge: str) -> str:
    return (
        f"{VK_ID_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={VK_CLIENT_ID}"
        f"&redirect_uri={quote(VK_REDIRECT_URI, safe='')}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )


async def exchange_vk_code(code: str, code_verifier: str, device_id: str, state: str = "") -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            VK_ID_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": VK_CLIENT_ID,
                "code_verifier": code_verifier,
                "code": code,
                "redirect_uri": VK_REDIRECT_URI,
                "device_id": device_id,
                "state": state,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = resp.json()
        if "error" in data:
            raise HTTPException(status_code=400, detail=f"VK error: {data.get('error_description', data['error'])}")
        return data


async def get_vk_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            VK_ID_USER_INFO_URL,
            data={"client_id": VK_CLIENT_ID, "access_token": access_token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = resp.json()
        if "error" in data:
            raise HTTPException(status_code=400, detail=f"VK API error: {data.get('error_description', data['error'])}")
        return data.get("user", data)


def is_vk_id_allowed(vk_id: int) -> bool:
    return vk_id in get_allowed_vk_ids()


def get_or_create_user(db: Session, vk_id: int, first_name: str, last_name: str) -> User:
    vk_id_str = str(vk_id)
    user = db.query(User).filter(User.vk_id == vk_id_str).first()
    if user:
        return user
    user = User(vk_id=vk_id_str)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_oauth_cookies(response: Response, state: str, code_verifier: str):
    for key, value in [(STATE_COOKIE, state), (CODE_VERIFIER_COOKIE, code_verifier)]:
        response.set_cookie(
            key=key, value=value, max_age=COOKIE_TTL,
            httponly=True, samesite="lax", secure=True,
        )


def verify_state(request: Request) -> str:
    state = request.cookies.get(STATE_COOKIE)
    if not state:
        raise HTTPException(status_code=400, detail="OAuth state cookie not found")
    return state


def get_code_verifier(request: Request) -> str:
    verifier = request.cookies.get(CODE_VERIFIER_COOKIE)
    if not verifier:
        raise HTTPException(status_code=400, detail="OAuth code verifier cookie not found")
    return verifier


async def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, sub)
    if user is None:
        raise credentials_exception
    if not is_vk_id_allowed(int(user.vk_id)):
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return user


def verify_launch_params(query_params: dict) -> int | None:
    """
    Проверяет подпись launch params VK Mini App (HMAC-SHA256).
    Возвращает vk_user_id, если подпись верна, иначе None.
    """
    if not VK_APP_SECRET:
        return None

    sign = query_params.get("sign")
    if not sign:
        return None

    vk_params = {k: v for k, v in query_params.items() if k.startswith("vk_")}
    if not vk_params:
        return None

    sorted_keys = sorted(vk_params.keys())
    query_string = "&".join(f"{k}={vk_params[k]}" for k in sorted_keys)

    import hmac
    digest = hmac.new(
        VK_APP_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")

    if hmac.compare_digest(computed, sign):
        return int(vk_params["vk_user_id"])

    return None
