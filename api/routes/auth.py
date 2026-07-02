from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from db import get_db
from auth import (
    create_access_token, get_current_admin,
    get_vk_login_url, exchange_vk_code, get_vk_user_info,
    is_vk_id_allowed, get_or_create_user,
    generate_state, generate_code_verifier, compute_code_challenge,
    generate_device_id, set_oauth_cookies, verify_state, get_code_verifier,
    get_allowed_vk_ids, ACCESS_TOKEN_EXPIRE_MINUTES,
)
from config import DEV_LOGIN_ENABLED, FRONTEND_URL
from datetime import timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/vk-login")
def vk_login(response: Response):
    state = generate_state()
    code_verifier = generate_code_verifier()
    code_challenge = compute_code_challenge(code_verifier)
    set_oauth_cookies(response, state, code_verifier)
    url = get_vk_login_url(state, code_challenge)
    return {"url": url}


@router.get("/vk-callback")
async def vk_callback(
    code: str,
    state: str,
    request: Request,
    device_id: str = "",
    db: Session = Depends(get_db),
):
    expected_state = verify_state(request)
    if state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    code_verifier = get_code_verifier(request)
    if not device_id:
        device_id = generate_device_id()

    token_data = await exchange_vk_code(code, code_verifier, device_id, state)
    vk_access_token = token_data["access_token"]
    user_info = await get_vk_user_info(vk_access_token)
    vk_user_id = user_info.get("user_id")
    if not vk_user_id:
        raise HTTPException(status_code=400, detail="VK user_id not found")

    if not is_vk_id_allowed(int(vk_user_id)):
        raise HTTPException(status_code=403, detail="Доступ запрещён. Обратитесь к администратору.")

    get_or_create_user(db, vk_user_id, "", "")

    access_token = create_access_token(
        data={"sub": str(vk_user_id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response = RedirectResponse(url=f"{FRONTEND_URL}/admin/login?token={access_token}", status_code=302)
    response.delete_cookie("vk_oauth_state")
    response.delete_cookie("vk_code_verifier")
    return response


@router.get("/me")
def read_me(admin: dict = Depends(get_current_admin)):
    return {"id": admin.vk_id, "vk_id": admin.vk_id}


@router.get("/config")
def auth_config():
    return {"dev_login_enabled": DEV_LOGIN_ENABLED}


@router.post("/dev-login")
def dev_login(db: Session = Depends(get_db)):
    if not DEV_LOGIN_ENABLED:
        raise HTTPException(status_code=404, detail="Not Found")

    allowed = get_allowed_vk_ids()
    if not allowed:
        raise HTTPException(status_code=500, detail="VK_ALLOWED_IDS пуст")

    vk_id = sorted(allowed)[0]
    user = get_or_create_user(db, vk_id, "", "")

    access_token = create_access_token(
        data={"sub": str(user.vk_id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}
