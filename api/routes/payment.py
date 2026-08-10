import json
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote_plus
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import config
from db import get_db
from models import DragonSet, PaymentOrder, User, PaymentLog
from services.payment_service import (
    is_donor, calc_set_price, count_available, select_dragons,
    get_active_provider, is_payment_blocked_for,
)

router = APIRouter(prefix="/api/payment", tags=["payment"])

ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


MSK = timezone(timedelta(hours=3))


def _now_msk() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%dT%H:%M:%S")


def _md5(raw: str) -> str:
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def inv_id_for_order(order_id: int) -> int:
    return order_id + config.ROBOKASSA_INV_ID_OFFSET


def order_id_from_inv(inv_id: int) -> int:
    return inv_id - config.ROBOKASSA_INV_ID_OFFSET


def _is_order_expired(order: PaymentOrder) -> bool:
    if not order or order.status != "pending":
        return False
    if not order.created_at:
        return False
    try:
        created = datetime.strptime(order.created_at, "%Y-%m-%dT%H:%M:%S")
        return (datetime.now() - created) > timedelta(hours=1)
    except (ValueError, TypeError):
        return False


def _cancel_expired_orders(db: Session, vk_id: int = None):
    q = db.query(PaymentOrder).filter(PaymentOrder.status == "pending")
    if vk_id is not None:
        q = q.filter(PaymentOrder.vk_id == vk_id)
    expired = []
    for order in q.all():
        if _is_order_expired(order):
            order.status = "cancelled"
            expired.append(order)
    if expired:
        db.commit()
        import sys
        for o in expired:
            print(f"[Payment] Auto-cancelled expired order #{o.id} for vk_id={o.vk_id}", file=sys.stderr)
    return expired


def build_receipt(out_sum: str, order: PaymentOrder, description: str) -> str:
    total = float(out_sum)
    name = f"{description or 'Набор драконов'} - {out_sum}"
    items = [{
        "name": name,
        "quantity": 1,
        "sum": total,
        "tax": "none",
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
            created_at=_now_msk(),
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
    inv_id = str(inv_id_for_order(order.id))
    receipt = build_receipt(out_sum, order, description)
    receipt_encoded = quote_plus(receipt, safe="")
    password1 = config.robokassa_password1()
    sig_raw = f"{login}:{out_sum}:{inv_id}:{receipt_encoded}:{password1}:Shp_vk_id={vk_id}"
    signature = _md5(sig_raw)
    pass_masked = f"***({len(password1)})" if password1 else "EMPTY"
    sig_display = f"{login}:{out_sum}:{inv_id}:<receipt>:{pass_masked}:Shp_vk_id={vk_id}"
    import sys
    print(
        f"[Robokassa API] {sig_display} sig={signature}",
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
                 config.robokassa_is_test(), signature, receipt,
                 f"{sig_display}\nreceipt={receipt}")
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
            DragonReservation.vk_user_id == vk_id,
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
        from bot.keyboard import garden_row, bestiary_link_row, _keyboard, row
        kb = _keyboard([
            row(("\u26a1 Активировать все", "activate_all")),
            garden_row(),
            bestiary_link_row(),
        ])
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

    if is_payment_blocked_for(vk_id, db):
        return {"error": "unavailable"}

    _cancel_expired_orders(db, vk_id)

    pending = db.query(PaymentOrder).filter(
        PaymentOrder.vk_id == vk_id,
        PaymentOrder.status == "pending",
    ).first()
    if pending:
        if _is_order_expired(pending):
            pending.status = "cancelled"
            db.commit()
        else:
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

    provider = get_active_provider(db)
    order = PaymentOrder(
        vk_id=vk_id,
        set_id=set_id,
        amount_rub=amount,
        quantity=quantity,
        price_per_pin=price_per_pin,
        provider=provider,
        status="pending",
        dragon_ids="[]",
        created_at=_now(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    url = f"{config.SITE_URL}/api/payment/pay/{order.id}?vk_id={vk_id}"
    return {
        "payment_url": url,
        "order_id": order.id,
        "amount_rub": amount,
        "quantity": quantity,
        "provider": provider,
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
    inv_id_raw = params.get("InvId")
    signature = params.get("SignatureValue")
    shp_vk_id = params.get("Shp_vk_id")
    if not (out_sum and inv_id_raw and signature and shp_vk_id):
        _log_payment(0, 0, "callback_bad_params", "", out_sum or "", inv_id_raw or "",
                     False, signature or "", "", f"missing params: OutSum={out_sum} InvId={inv_id_raw} Sig={signature} Shp={shp_vk_id}")
        raise HTTPException(status_code=400, detail="bad params")

    if not verify_result_signature(out_sum, inv_id_raw, signature, shp_vk_id):
        _log_payment(int(shp_vk_id), 0, "callback_bad_sig", "", out_sum, inv_id_raw,
                     False, signature or "", "", "bad signature")
        raise HTTPException(status_code=400, detail="bad signature")

    real_order_id = order_id_from_inv(int(inv_id_raw))
    order = db.query(PaymentOrder).filter(PaymentOrder.id == real_order_id).first()
    if not order:
        _log_payment(int(shp_vk_id), int(inv_id_raw), "callback_order_not_found", "",
                     out_sum, inv_id_raw, False, signature or "", "",
                     f"order_id={real_order_id} not found for inv_id={inv_id_raw}")
        raise HTTPException(status_code=400, detail="order not found")

    if order.status == "success":
        return PlainTextResponse(f"OK{inv_id_raw}")

    if order.status == "cancelled":
        _log_payment(order.vk_id, order.id, "callback_cancelled", "", out_sum, inv_id_raw,
                     False, signature or "", "", "order was cancelled")
        return PlainTextResponse(f"OK{inv_id_raw}")

    if int(shp_vk_id) != order.vk_id:
        _log_payment(order.vk_id, order.id, "callback_vk_mismatch", "",
                     out_sum, inv_id_raw, False, signature or "", "",
                     f"expected vk_id={order.vk_id} got={shp_vk_id}")
        raise HTTPException(status_code=400, detail="vk_id mismatch")

    paid = round(float(out_sum) * 100)
    if abs(paid - order.amount_rub) > 1:
        _log_payment(order.vk_id, order.id, "callback_amount_mismatch", "",
                     out_sum, inv_id_raw, False, signature or "", "",
                     f"expected={order.amount_rub} got={paid}")
        raise HTTPException(status_code=400, detail="amount mismatch")

    dragons = select_dragons(order.vk_id, order.quantity, db)
    order.status = "success"
    order.completed_at = _now()
    order.robokassa_inv_id = int(inv_id_raw)
    order.dragon_ids = json.dumps([d.id for d in dragons])
    db.commit()

    order.notified = _send_pins(order.vk_id, dragons, db)
    db.commit()

    _log_payment(order.vk_id, order.id, "callback_success", "", out_sum, inv_id_raw,
                 False, signature or "", order.dragon_ids, f"dragons={order.dragon_ids}", db)

    return PlainTextResponse(f"OK{inv_id_raw}")


@router.get("/pay/{order_id}", response_class=HTMLResponse)
def payment_post_redirect(request: Request, order_id: int, vk_id: int, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else ""
    order = db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()
    if not order:
        _log_payment(vk_id, order_id, "pay_not_found", "", "", "", False, "", "",
                     f"order_id={order_id} not found (ip={client_ip})", db=db)
        return HTMLResponse("<h1>Заказ не найден</h1>", status_code=404)
    if _is_order_expired(order):
        _log_payment(vk_id, order_id, "pay_expired", "", "", "", False, "", "",
                     f"order_id={order_id} expired, was status={order.status} (ip={client_ip})", db=db)
        return HTMLResponse(
            "<h1>Заказ просрочен</h1><p>Время оплаты истекло (1 час). Создай новый заказ.</p>",
            status_code=410,
        )
    if order.status != "pending":
        _log_payment(vk_id, order_id, f"pay_already_{order.status}", "", "", "", False, "", "",
                     f"order_id={order_id} status={order.status} amount_rub={order.amount_rub} (ip={client_ip})", db=db)
        return HTMLResponse(f"<h1>Заказ уже {order.status}</h1>", status_code=400)

    dset = db.query(DragonSet).filter(DragonSet.id == order.set_id).first()
    description = f"Набор «{dset.name}»" if dset else "Набор драконов"

    provider = order.provider or "robokassa"
    if provider == "moneta":
        from services.moneta_service import build_payment_signature, format_amount, moneta_transaction_id_for

        mnt_id = config.MONETA_MNT_ID
        mnt_trx = moneta_transaction_id_for(order.id)
        amount_str = format_amount(order.amount_rub)
        test_mode = "1" if config.moneta_is_test() else "0"
        signature = build_payment_signature(
            mnt_id, mnt_trx, amount_str, config.MONETA_INTEGRITY_CODE, test_mode,
        )
        no_sig = config.MONETA_NO_SIGNATURE_FORM

        _log_payment(vk_id, order.id, "moneta_form_created", mnt_id, amount_str, mnt_trx,
                     config.moneta_is_test(), signature, "",
                     f"POST redirect | mnt_id={mnt_id} mnt_trx={mnt_trx} amount={amount_str} no_sig={no_sig} (ip={client_ip})")

        fields = [
            ("MNT_ID", mnt_id),
            ("MNT_TRANSACTION_ID", mnt_trx),
            ("MNT_CURRENCY_CODE", "RUB"),
            ("MNT_AMOUNT", amount_str),
            ("MNT_DESCRIPTION", description),
            ("MNT_TEST_MODE", test_mode),
            ("MNT_SUCCESS_URL", f"{config.SITE_URL}/api/payment/success"),
            ("MNT_FAIL_URL", f"{config.SITE_URL}/api/payment/fail"),
            ("MNT_RETURN_URL", f"{config.SITE_URL}/api/payment/return"),
        ]
        if not no_sig:
            fields.append(("MNT_SIGNATURE", signature))

        inputs = "\n".join(
            f'<input type="hidden" name="{k}" value="{v}" />'
            for k, v in fields
        )

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Оплата</title></head>
<body style="background:#1a1a2e;color:#e0d6c2;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center">
<p>Перенаправление на страницу оплаты...</p>
<form id="f" action="{config.moneta_assistant_url()}" method="POST">
{inputs}
</form>
<script>document.getElementById('f').submit();</script>
</div>
</body></html>"""

        return HTMLResponse(html)

    login = config.ROBOKASSA_MERCHANT_LOGIN

    out_sum = f"{order.amount_rub / 100:.2f}"
    inv_id = str(inv_id_for_order(order.id))
    receipt = build_receipt(out_sum, order, description)
    receipt_encoded = quote_plus(receipt, safe="")
    password1 = config.robokassa_password1()
    sig_raw = f"{login}:{out_sum}:{inv_id}:{receipt_encoded}:{password1}:Shp_vk_id={vk_id}"
    signature = _md5(sig_raw)

    _log_payment(vk_id, order.id, "url_created", login, out_sum, inv_id,
                 config.robokassa_is_test(), signature, receipt,
                 f"POST redirect | login={login} out_sum={out_sum} inv_id={inv_id}")

    fields = [
        ("MerchantLogin", login),
        ("OutSum", out_sum),
        ("InvId", inv_id),
        ("Description", description),
        ("SignatureValue", signature),
        ("Shp_vk_id", str(vk_id)),
        ("Receipt", receipt_encoded),
        ("Culture", "ru"),
        ("Encoding", "utf-8"),
    ]
    if config.robokassa_is_test():
        fields.append(("IsTest", "1"))

    inputs = "\n".join(
        f'<input type="hidden" name="{k}" value="{v}" />'
        for k, v in fields
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Оплата</title></head>
<body style="background:#1a1a2e;color:#e0d6c2;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center">
<p>Перенаправление на страницу оплаты...</p>
<form id="f" action="{ROBOKASSA_URL}" method="POST">
{inputs}
</form>
<script>document.getElementById('f').submit();</script>
</div>
</body></html>"""

    return HTMLResponse(html)


@router.get("/success")
def payment_success(InvId: str = "", Culture: str = "ru"):
    return RedirectResponse(config.VK_GROUP_URL, status_code=302)


@router.get("/fail")
def payment_fail(InvId: str = "", Culture: str = "ru"):
    return RedirectResponse(config.VK_GROUP_URL, status_code=302)


@router.get("/return")
def payment_return():
    return RedirectResponse(config.VK_GROUP_URL, status_code=302)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.api_route("/moneta/callback", methods=["GET", "POST"])
async def moneta_callback(request: Request, db: Session = Depends(get_db)):
    client_ip = _client_ip(request)
    from services.moneta_service import verify_callback_signature, order_id_from_moneta

    params = dict(request.query_params)
    try:
        form = await request.form()
        params.update({k: v for k, v in form.items()})
    except Exception:
        pass

    _log_payment(0, 0, "moneta_callback_raw", "", params.get("MNT_AMOUNT", ""), params.get("MNT_TRANSACTION_ID", ""),
                 False, params.get("MNT_SIGNATURE", ""), "", f"ip={client_ip} params={params}")

    mnt_transaction_id = params.get("MNT_TRANSACTION_ID")
    mnt_amount = params.get("MNT_AMOUNT")
    signature = params.get("MNT_SIGNATURE")

    no_sig_cb = config.MONETA_NO_SIGNATURE_CALLBACK

    if not (mnt_transaction_id and mnt_amount and (signature or no_sig_cb)):
        _log_payment(0, 0, "moneta_callback_bad_params", "", mnt_amount or "", mnt_transaction_id or "",
                     False, signature or "", "", f"ip={client_ip} params={params}")
        raise HTTPException(status_code=400, detail="bad params")

    if no_sig_cb:
        if client_ip not in config.MONETA_CALLBACK_IPS:
            _log_payment(0, 0, "moneta_callback_bad_ip", "", mnt_amount, mnt_transaction_id,
                         False, signature or "", "", f"ip={client_ip} allowed={config.MONETA_CALLBACK_IPS}")
            raise HTTPException(status_code=400, detail="bad ip")
    elif not verify_callback_signature(params, config.MONETA_INTEGRITY_CODE):
        _log_payment(0, 0, "moneta_callback_bad_sig", "", mnt_amount, mnt_transaction_id,
                     False, signature or "", "", f"ip={client_ip} params={params}")
        raise HTTPException(status_code=400, detail="bad signature")

    real_order_id = order_id_from_moneta(mnt_transaction_id)
    if real_order_id is None:
        _log_payment(0, 0, "moneta_callback_bad_order_id", "", mnt_amount, mnt_transaction_id,
                     False, signature or "", "", f"ip={client_ip}")
        raise HTTPException(status_code=400, detail="bad order_id")

    order = db.query(PaymentOrder).filter(PaymentOrder.id == real_order_id).first()
    if not order:
        _log_payment(0, real_order_id, "moneta_callback_order_not_found", "", mnt_amount, mnt_transaction_id,
                     False, signature or "", "", f"ip={client_ip}")
        raise HTTPException(status_code=400, detail="order not found")

    if order.status == "success":
        return PlainTextResponse("SUCCESS")

    if order.status == "cancelled":
        _log_payment(order.vk_id, order.id, "moneta_callback_cancelled", "", mnt_amount, mnt_transaction_id,
                     False, signature or "", "", f"ip={client_ip}")
        return PlainTextResponse("SUCCESS")

    try:
        paid = round(float(mnt_amount) * 100)
    except (ValueError, TypeError):
        paid = -1
    if abs(paid - order.amount_rub) > 1:
        _log_payment(order.vk_id, order.id, "moneta_callback_amount_mismatch", "", mnt_amount, mnt_transaction_id,
                     False, signature or "", "",
                     f"expected={order.amount_rub} got={paid} ip={client_ip}")
        raise HTTPException(status_code=400, detail="amount mismatch")

    dragons = select_dragons(order.vk_id, order.quantity, db)
    order.status = "success"
    order.completed_at = _now()
    order.dragon_ids = json.dumps([d.id for d in dragons])
    db.commit()

    order.notified = _send_pins(order.vk_id, dragons, db)
    db.commit()

    mnt_operation_id = params.get("MNT_OPERATION_ID", "")
    _log_payment(order.vk_id, order.id, "moneta_callback_success", "", mnt_amount, mnt_transaction_id,
                 False, signature or "", order.dragon_ids,
                 f"dragons={order.dragon_ids} mnt_operation_id={mnt_operation_id} ip={client_ip}", db)

    return PlainTextResponse("SUCCESS")
