import json
import hashlib
from datetime import datetime
from urllib.parse import urlencode, quote_plus
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session
import config
from db import get_db
from models import DragonSet, PaymentOrder, User, PaymentLog
from services.payment_service import (
    is_donor, calc_set_price, count_available, select_dragons,
)

router = APIRouter(prefix="/api/payment", tags=["payment"])

ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _md5(raw: str) -> str:
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def build_receipt(out_sum: str, order: PaymentOrder, description: str) -> str:
    items = [{
        "name": description or "Набор драконов",
        "quantity": order.quantity,
        "sum": float(out_sum),
        "tax": "none",
        "payment_method": "full_payment",
        "payment_object": "commodity",
    }]
    return json.dumps({"items": items}, separators=(",", ":"), ensure_ascii=False)


def _log_payment(vk_id: int, order_id: int, action: str, login: str,
                 out_sum: str, inv_id: str, test_mode: bool, sig: str,
                 receipt_json: str, detail: str = "", db: Session = None):
    try:
        if db is None:
            from db import SessionLocal
            db = SessionLocal()
            own_db = True
        else:
            own_db = False
        log = PaymentLog(
            vk_id=vk_id,
            order_id=order_id,
            action=action,
            login=login,
            out_sum=out_sum,
            inv_id=inv_id,
            test_mode=test_mode,
            sig=sig,
            receipt_json=receipt_json,
            detail=detail,
            created_at=_now(),
        )
        db.add(log)
        db.commit()
    except Exception:
        pass
    finally:
        if own_db:
            db.close()


def build_payment_url(order: PaymentOrder, vk_id: int, description: str) -> str:
    login = config.ROBOKASSA_MERCHANT_LOGIN
    out_sum = f"{order.amount_rub / 100:.2f}"
    inv_id = str(order.id)
    receipt = build_receipt(out_sum, order, description)
    receipt_encoded = quote_plus(receipt, safe="")
    password1 = config.robokassa_password1()
    sig_raw = f"{login}:{out_sum}:{inv_id}:{receipt_encoded}:{password1}:Shp_vk_id={vk_id}"
    signature = _md5(sig_raw)
    import sys
    print(
        f"[Robokassa API] login={login} out_sum={out_sum} inv_id={inv_id} "
        f"test_mode={config.robokassa_is_test()} "
        f"pass1_empty={not bool(password1)} pass1_len={len(password1)} "
        f"sig={signature} receipt_len={len(receipt_encoded)} "
        f"sig_raw={login}:{out_sum}:{inv_id}:<receipt>:{'***' if password1 else 'EMPTY'}:Shp_vk_id={vk_id}",
        file=sys.stderr, flush=True,
    )
    params = {
        "MerchantLogin": login,
        "OutSum": out_sum,
        "InvId": inv_id,
        "Description": description,
        "SignatureValue": signature,
        "Shp_vk_id": str(vk_id),
        "Culture": "ru",
        "Encoding": "utf-8",
    }
    if config.robokassa_is_test():
        params["IsTest"] = "1"
    query = urlencode(params)
    _log_payment(vk_id, order.id, "url_created", login, out_sum, inv_id,
                 config.robokassa_is_test(), signature, receipt, "")
    return f"{ROBOKASSA_URL}?Receipt={receipt_encoded}&{query}"


def verify_result_signature(out_sum: str, inv_id: str, signature: str, vk_id: str) -> bool:
    expected = _md5(
        f"{out_sum}:{inv_id}:{config.robokassa_password2()}:Shp_vk_id={vk_id}"
    )
    return expected.lower() == (signature or "").lower()


def _send_pins(vk_id: int, dragons: list, db=None) -> bool:
    from routes.admin import _notify_user
    from models import DragonReservation

    now_str = _now()
    for d in dragons:
        existing = db.query(DragonReservation).filter(
            DragonReservation.dragon_id == d.id,
            DragonReservation.is_activated == False,
        ).first() if db else None
        if not existing and db:
            reservation = DragonReservation(
                vk_url=f"https://vk.ru/id{vk_id}",
                vk_user_id=vk_id,
                dragon_id=d.id,
                is_activated=False,
                notes="Покупка через Robokassa",
                created_at=now_str,
                updated_at=now_str,
            )
            db.add(reservation)
            try:
                import config as _cfg
                if _cfg.VK_GROUP_TOKEN:
                    import vk_api as _vk
                    _vk_obj = _vk.VkApi(token=_cfg.VK_GROUP_TOKEN, api_version="5.199").get_api()
                    users = _vk_obj.users.get(user_ids=str(vk_id), fields="first_name,last_name")
                    if users:
                        u = users[0]
                        reservation.vk_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
            except Exception:
                pass
    if db:
        db.commit()

    lines = [f"🥚 {d.pin_code}" for d in dragons]
    message = (
        "🎉 Покупка прошла успешно!\n\n"
        "Твои PIN-коды:\n" + "\n".join(lines)
    )
    try:
        import random
        if not config.VK_GROUP_TOKEN:
            return False
        import vk_api
        from bot.keyboard import garden_row, bestiary_link_row, _keyboard
        kb = _keyboard([garden_row(), bestiary_link_row()])
        vk = vk_api.VkApi(token=config.VK_GROUP_TOKEN, api_version="5.199").get_api()
        vk.messages.send(
            user_id=vk_id,
            message=message,
            random_id=random.randint(1, 2 ** 31 - 1),
            keyboard=kb,
        )
        return True
    except Exception:
        return False


@router.post("/create-order")
async def create_order(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = {}
    vk_id = body.get("vk_id")
    set_id = body.get("set_id")
    accept_partial = bool(body.get("accept_partial", False))
    if vk_id is None or set_id is None:
        raise HTTPException(status_code=400, detail="vk_id and set_id required")
    vk_id = int(vk_id)
    set_id = int(set_id)

    pending = db.query(PaymentOrder).filter(
        PaymentOrder.vk_id == vk_id,
        PaymentOrder.status == "pending",
    ).first()
    if pending:
        return {"error": "pending", "order_id": pending.id}

    dset = db.query(DragonSet).filter(
        DragonSet.id == set_id, DragonSet.is_active == True
    ).first()
    if not dset:
        raise HTTPException(status_code=404, detail="Set not found")

    donor = is_donor(vk_id, db)
    total, price_per_pin = calc_set_price(dset, donor, vk_id, db)

    available = count_available(vk_id, db)
    if available <= 0:
        return {"error": "no_dragons"}

    quantity = dset.quantity
    amount = total
    if available < dset.quantity:
        if not accept_partial:
            return {
                "error": "partial",
                "available": available,
                "partial_price": available * price_per_pin,
                "price_per_pin": price_per_pin,
            }
        quantity = available
        amount = available * price_per_pin

    order = PaymentOrder(
        vk_id=vk_id,
        set_id=set_id,
        amount_rub=amount,
        quantity=quantity,
        price_per_pin=price_per_pin,
        status="pending",
        dragon_ids="[]",
        created_at=_now(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    url = build_payment_url(order, vk_id, f"Набор «{dset.name}»")
    return {
        "payment_url": url,
        "order_id": order.id,
        "amount_rub": amount,
        "quantity": quantity,
    }


@router.api_route("/result", methods=["GET", "POST"])
async def payment_result(request: Request, db: Session = Depends(get_db)):
    params = dict(request.query_params)
    try:
        form = await request.form()
        params.update({k: v for k, v in form.items()})
    except Exception:
        pass

    out_sum = params.get("OutSum")
    inv_id = params.get("InvId")
    signature = params.get("SignatureValue")
    shp_vk_id = params.get("Shp_vk_id")
    if not (out_sum and inv_id and signature and shp_vk_id):
        raise HTTPException(status_code=400, detail="bad params")

    if not verify_result_signature(out_sum, inv_id, signature, shp_vk_id):
        try:
            _log_payment(int(shp_vk_id), int(inv_id), "callback_bad_sig", "", out_sum, inv_id,
                         False, signature or "", "", "bad signature", db)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="bad signature")

    order = db.query(PaymentOrder).filter(PaymentOrder.id == int(inv_id)).first()
    if not order:
        raise HTTPException(status_code=400, detail="order not found")

    if order.status == "success":
        return PlainTextResponse(f"OK{inv_id}")

    if int(shp_vk_id) != order.vk_id:
        raise HTTPException(status_code=400, detail="vk_id mismatch")

    paid = round(float(out_sum) * 100)
    if abs(paid - order.amount_rub) > 1:
        raise HTTPException(status_code=400, detail="amount mismatch")

    dragons = select_dragons(order.vk_id, order.quantity, db)
    order.status = "success"
    order.completed_at = _now()
    order.robokassa_inv_id = int(inv_id)
    order.dragon_ids = json.dumps([d.id for d in dragons])
    db.commit()

    order.notified = _send_pins(order.vk_id, dragons, db)
    db.commit()

    _log_payment(order.vk_id, order.id, "callback_success", "", out_sum, inv_id,
                 False, signature or "", order.dragon_ids, f"dragons={order.dragon_ids}", db)

    return PlainTextResponse(f"OK{inv_id}")


@router.get("/success")
def payment_success(InvId: str = "", Culture: str = "ru"):
    return RedirectResponse(config.VK_GROUP_URL, status_code=302)


@router.get("/fail")
def payment_fail(InvId: str = "", Culture: str = "ru"):
    return RedirectResponse(config.VK_GROUP_URL, status_code=302)
