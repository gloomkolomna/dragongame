"""Buy eggs handler — show packs from DB and generate Robokassa payment links."""

import hashlib
import json
from datetime import datetime
from urllib.parse import urlencode, quote

ROBOKASSA_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _md5(raw: str) -> str:
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _build_receipt(out_sum: str, order, description: str) -> str:
    items = [{
        "name": description or "Набор драконов",
        "quantity": order.quantity,
        "sum": float(out_sum),
        "tax": "none",
        "payment_method": "full_payment",
        "payment_object": "commodity",
    }]
    return json.dumps({"items": items}, separators=(",", ":"), ensure_ascii=False)


def _build_payment_url(order, vk_id: int, description: str) -> str:
    import config
    login = config.ROBOKASSA_MERCHANT_LOGIN
    out_sum = f"{order.amount_rub / 100:.2f}"
    inv_id = str(order.id)
    receipt = _build_receipt(out_sum, order, description)
    receipt_encoded = quote(receipt, safe="")
    signature = _md5(
        f"{login}:{out_sum}:{inv_id}:{receipt_encoded}:{config.robokassa_password1()}:Shp_vk_id={vk_id}"
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
    return f"{ROBOKASSA_URL}?Receipt={receipt_encoded}&{query}"


def _store_payment(user, order_id, db):
    sd = json.loads(user.state_data or "{}")
    sd["_payment_order_id"] = order_id
    user.state_data = json.dumps(sd, ensure_ascii=False)
    db.commit()


def handle_buy_eggs(user, db, send_message):
    from models import DragonSet
    from services.payment_service import is_donor, calc_set_price

    sets = (
        db.query(DragonSet)
        .filter(DragonSet.is_active == True)
        .order_by(DragonSet.sort_order)
        .all()
    )
    if not sets:
        send_message("🛒 Пока нет доступных наборов для покупки.")
        return

    donor = is_donor(user.vk_id, db)

    set_data = []
    for s in sets:
        total, _ = calc_set_price(s, donor, user.vk_id, db)
        discount = s.donor_discount_percent if donor else s.discount_percent
        set_data.append({
            "id": s.id,
            "name": s.name,
            "quantity": s.quantity,
            "price_rub": total // 100,
            "discount_percent": discount,
        })

    from bot.keyboard import buy_eggs_keyboard

    lines = ["🛒 Доступные наборы яиц:\n"]
    if donor:
        lines.append("💎 У тебя статус дона — цены со скидкой!\n")
    for sd in set_data:
        disc = f" (-{sd['discount_percent']}%)" if sd["discount_percent"] else ""
        lines.append(f"🥚 {sd['name']} — {sd['quantity']} шт. за {sd['price_rub']} ₽{disc}")
    lines.append("\nВыбери набор:")

    send_message("\n".join(lines), keyboard=buy_eggs_keyboard(set_data))


def handle_buy_set(user, set_id, db, send_message):
    from models import DragonSet, PaymentOrder
    from services.payment_service import is_donor, calc_set_price, count_available

    dset = db.query(DragonSet).filter(
        DragonSet.id == set_id, DragonSet.is_active == True
    ).first()
    if not dset:
        send_message("❌ Набор не найден или уже недоступен.")
        return

    pending = db.query(PaymentOrder).filter(
        PaymentOrder.vk_id == user.vk_id,
        PaymentOrder.status == "pending",
    ).first()
    if pending:
        _store_payment(user, pending.id, db)
        pending_dset = db.query(DragonSet).filter(DragonSet.id == pending.set_id).first()
        set_name = pending_dset.name if pending_dset else "?"
        price_rub = pending.amount_rub // 100
        from bot.keyboard import payment_link_keyboard
        send_message(
            f"⚠ У тебя уже есть неоплаченный заказ:\n"
            f"🛒 Набор «{set_name}» — {pending.quantity} шт. за {price_rub} ₽\n\n"
            f"Нажми кнопку ниже, чтобы перейти к оплате.",
            keyboard=payment_link_keyboard(),
        )
        return

    donor = is_donor(user.vk_id, db)
    total, price_per_pin = calc_set_price(dset, donor, user.vk_id, db)

    available = count_available(user.vk_id, db)
    if available <= 0:
        send_message("❌ К сожалению, все доступные драконы уже куплены.")
        return

    quantity = dset.quantity
    amount = total
    if available < dset.quantity:
        price_rub = (available * price_per_pin) // 100
        send_message(
            f"⚠ Доступно только {available} драконов из {dset.quantity}.\n"
            f"Стоимость частичного набора: {price_rub} ₽.\n"
            f"Отправь «ок», чтобы согласиться, или выбери другой набор."
        )
        sd = json.loads(user.state_data or "{}")
        sd["_partial_set_id"] = set_id
        sd["_partial_quantity"] = available
        sd["_partial_amount"] = available * price_per_pin
        user.state_data = json.dumps(sd, ensure_ascii=False)
        db.commit()
        return

    amount_rub = amount // 100
    order = PaymentOrder(
        vk_id=user.vk_id,
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

    _store_payment(user, order.id, db)
    from bot.keyboard import payment_link_keyboard

    donor_text = " (дон-скидка)" if donor else ""
    send_message(
        f"🛒 Набор «{dset.name}»\n"
        f"🥚 {quantity} шт.\n"
        f"💰 {amount_rub} ₽{donor_text}\n\n"
        f"Нажми кнопку ниже, чтобы перейти к оплате:",
        keyboard=payment_link_keyboard(),
    )


def handle_partial_confirm(user, db, send_message):
    from models import DragonSet, PaymentOrder
    from services.payment_service import is_donor

    sd = json.loads(user.state_data or "{}")
    set_id = sd.pop("_partial_set_id", None)
    quantity = sd.pop("_partial_quantity", None)
    amount = sd.pop("_partial_amount", None)
    user.state_data = json.dumps(sd, ensure_ascii=False)

    if not set_id or not quantity or not amount:
        db.commit()
        send_message("❌ Не удалось оформить заказ. Попробуй снова.")
        return

    dset = db.query(DragonSet).filter(DragonSet.id == set_id).first()
    if not dset:
        db.commit()
        send_message("❌ Набор не найден.")
        return

    donor = is_donor(user.vk_id, db)

    order = PaymentOrder(
        vk_id=user.vk_id,
        set_id=set_id,
        amount_rub=amount,
        quantity=quantity,
        price_per_pin=amount // quantity,
        status="pending",
        dragon_ids="[]",
        created_at=_now(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    _store_payment(user, order.id, db)
    from bot.keyboard import payment_link_keyboard

    amount_rub = amount // 100
    donor_text = " (дон-скидка)" if donor else ""
    send_message(
        f"🛒 Набор «{dset.name}» (частичный)\n"
        f"🥚 {quantity} шт.\n"
        f"💰 {amount_rub} ₽{donor_text}\n\n"
        f"Нажми кнопку ниже, чтобы перейти к оплате:",
        keyboard=payment_link_keyboard(),
    )


def handle_open_payment(user, db, send_message):
    from models import PaymentOrder, DragonSet

    sd = json.loads(user.state_data or "{}")
    order_id = sd.get("_payment_order_id")
    if not order_id:
        send_message("❌ Заказ не найден. Попробуй выбрать набор заново.")
        return

    order = db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()
    if not order:
        send_message("❌ Заказ не найден.")
        return

    dset = db.query(DragonSet).filter(DragonSet.id == order.set_id).first()
    set_name = dset.name if dset else "?"
    url = _build_payment_url(order, user.vk_id, f"Набор «{set_name}»")

    send_message(
        f"💳 Ссылка для оплаты набора «{set_name}»:\n{url}",
        keyboard=json.dumps({
            "one_time": False,
            "buttons": [
                [{
                    "action": {
                        "type": "open_link",
                        "label": "💳 Перейти к оплате",
                        "link": url,
                    },
                }],
            ],
        }, ensure_ascii=False),
    )
