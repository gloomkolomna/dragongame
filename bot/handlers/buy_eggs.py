"""Buy eggs handler — show packs from DB and generate payment links."""

import json
import re
from datetime import datetime

OFFERTA_TEXT = "\n\nПеред покупкой ознакомьтесь с условиями оферты: https://belovolovhome.ru/dragons/offerta.docx"

PAYMENTS_UNAVAILABLE = "💳 Оплата временно недоступна — идут технические работы. Зайдите, пожалуйста, позже!"

EMAIL_PROMPT = "📧 Для отправки чека об оплате (по 54-ФЗ) укажите ваш email:"
EMAIL_INVALID = "Похоже, это не email. Попробуйте ещё раз:"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _store_payment(user, order_id, db):
    sd = json.loads(user.state_data or "{}")
    sd["_payment_order_id"] = order_id
    user.state_data = json.dumps(sd, ensure_ascii=False)
    db.commit()


def handle_buy_eggs(user, db, send_message):
    from models import DragonSet
    from services.payment_service import is_donor, calc_set_price, is_payment_blocked_for

    if is_payment_blocked_for(user.vk_id, db):
        send_message(PAYMENTS_UNAVAILABLE)
        return

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

    send_message("\n".join(lines) + OFFERTA_TEXT, keyboard=buy_eggs_keyboard(set_data))


def _is_order_expired(order):
    if not order or order.status != "pending":
        return False
    if not order.created_at:
        return False
    try:
        from datetime import datetime, timedelta
        created = datetime.strptime(order.created_at, "%Y-%m-%dT%H:%M:%S")
        return (datetime.now() - created) > timedelta(hours=1)
    except (ValueError, TypeError):
        return False


def _ask_email(user, db, set_id, quantity, amount, price_per_pin):
    sd = json.loads(user.state_data or "{}")
    sd["_pending_buy_set_id"] = set_id
    sd["_pending_quantity"] = quantity
    sd["_pending_amount"] = amount
    sd["_pending_price_per_pin"] = price_per_pin
    user.state_data = json.dumps(sd, ensure_ascii=False)
    from bot.fsm import AWAIT_RECEIPT_EMAIL
    user.state = AWAIT_RECEIPT_EMAIL
    db.commit()
    from bot.keyboard import await_receipt_email_keyboard
    send = None
    return await_receipt_email_keyboard()


def _create_pending_order(user, db, set_id, quantity, amount, price_per_pin, email):
    from models import PaymentOrder
    from services.payment_service import get_active_provider
    order = PaymentOrder(
        vk_id=user.vk_id,
        set_id=set_id,
        amount_rub=amount,
        quantity=quantity,
        price_per_pin=price_per_pin,
        provider=get_active_provider(db),
        receipt_email=email.strip().lower(),
        status="pending",
        dragon_ids="[]",
        created_at=_now(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    _store_payment(user, order.id, db)
    return order


def handle_receipt_email(user, text, db, send_message):
    from bot.fsm import IDLE, AWAIT_RECEIPT_EMAIL
    email = (text or "").strip()
    if not _EMAIL_RE.match(email):
        from bot.keyboard import await_receipt_email_keyboard
        send_message(EMAIL_INVALID, keyboard=await_receipt_email_keyboard())
        return

    sd = json.loads(user.state_data or "{}")
    set_id = sd.pop("_pending_buy_set_id", None)
    quantity = sd.pop("_pending_quantity", None)
    amount = sd.pop("_pending_amount", None)
    price_per_pin = sd.pop("_pending_price_per_pin", None)
    user.state_data = json.dumps(sd, ensure_ascii=False)

    if set_id is None or quantity is None or amount is None:
        user.state = IDLE
        db.commit()
        send_message("❌ Не удалось оформить заказ. Попробуй снова.")
        return

    order = _create_pending_order(user, db, set_id, quantity, amount, price_per_pin, email)
    user.state = IDLE
    db.commit()

    from models import DragonSet
    dset = db.query(DragonSet).filter(DragonSet.id == set_id).first()
    set_name = dset.name if dset else "Набор драконов"
    amount_rub = amount // 100

    from bot.keyboard import payment_link_keyboard
    send_message(
        f"🛒 Набор «{set_name}»\n"
        f"🥚 {quantity} шт.\n"
        f"💰 {amount_rub} ₽\n\n"
        f"📧 Чек будет отправлен на {email}\n\n"
        f"💡 Ссылка на оплату действует 1 час.\n"
        f"Нажми кнопку ниже, чтобы перейти к оплате:"
        + OFFERTA_TEXT,
        keyboard=payment_link_keyboard(),
    )


def handle_buy_set(user, set_id, db, send_message):
    from models import DragonSet, PaymentOrder
    from services.payment_service import is_donor, calc_set_price, count_available, get_active_provider, is_payment_blocked_for

    dset = db.query(DragonSet).filter(
        DragonSet.id == set_id, DragonSet.is_active == True
    ).first()
    if not dset:
        send_message("❌ Набор не найден или уже недоступен.")
        return

    if is_payment_blocked_for(user.vk_id, db):
        send_message(PAYMENTS_UNAVAILABLE)
        return

    pending = db.query(PaymentOrder).filter(
        PaymentOrder.vk_id == user.vk_id,
        PaymentOrder.status == "pending",
    ).first()
    if pending:
        if _is_order_expired(pending):
            pending.status = "cancelled"
            db.commit()
        else:
            _store_payment(user, pending.id, db)
            pending_dset = db.query(DragonSet).filter(DragonSet.id == pending.set_id).first()
            set_name = pending_dset.name if pending_dset else "?"
            price_rub = pending.amount_rub // 100
            from bot.keyboard import payment_link_keyboard
            send_message(
                f"⚠ У тебя уже есть неоплаченный заказ:\n"
                f"🛒 Набор «{set_name}» — {pending.quantity} шт. за {price_rub} ₽\n\n"
                f"💡 Ссылка на оплату действует 1 час.\n"
                f"Нажми кнопку ниже, чтобы перейти к оплате."
                + OFFERTA_TEXT,
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
            + OFFERTA_TEXT
        )
        sd = json.loads(user.state_data or "{}")
        sd["_partial_set_id"] = set_id
        sd["_partial_quantity"] = available
        sd["_partial_amount"] = available * price_per_pin
        sd["_partial_price_per_pin"] = price_per_pin
        user.state_data = json.dumps(sd, ensure_ascii=False)
        db.commit()
        return

    kb = _ask_email(user, db, set_id, quantity, amount, price_per_pin)
    donor_text = " (дон-скидка)" if donor else ""
    amount_rub = amount // 100
    send_message(
        f"🛒 Набор «{dset.name}»\n"
        f"🥚 {quantity} шт.\n"
        f"💰 {amount_rub} ₽{donor_text}\n\n"
        + EMAIL_PROMPT,
        keyboard=kb,
    )


def handle_partial_confirm(user, db, send_message):
    from models import DragonSet

    sd = json.loads(user.state_data or "{}")
    set_id = sd.pop("_partial_set_id", None)
    quantity = sd.pop("_partial_quantity", None)
    amount = sd.pop("_partial_amount", None)
    price_per_pin = sd.pop("_partial_price_per_pin", None) or (amount // quantity if quantity else 0)
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

    kb = _ask_email(user, db, set_id, quantity, amount, price_per_pin)
    amount_rub = amount // 100
    send_message(
        f"🛒 Набор «{dset.name}» (частичный)\n"
        f"🥚 {quantity} шт.\n"
        f"💰 {amount_rub} ₽\n\n"
        + EMAIL_PROMPT,
        keyboard=kb,
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

    if _is_order_expired(order):
        order.status = "cancelled"
        db.commit()
        send_message("⏰ Срок оплаты заказа истёк (1 час). Создай новый заказ.")
        return

    if order.status == "cancelled":
        send_message("❌ Заказ отменён. Создай новый заказ.")
        return

    if order.status != "pending":
        send_message(f"❌ Статус заказа: {order.status}. Обратись в поддержку.")
        return

    dset = db.query(DragonSet).filter(DragonSet.id == order.set_id).first()
    set_name = dset.name if dset else "?"
    import config as _cfg
    url = f"{_cfg.SITE_URL}/api/payment/pay/{order.id}?vk_id={user.vk_id}"

    from bot.keyboard import garden_row, _keyboard
    payment_kb = _keyboard([
        [{
            "action": {
                "type": "open_link",
                "label": "💳 Перейти к оплате",
                "link": url,
            },
        }],
        [{
            "action": {
                "type": "text",
                "label": "❌ Отменить оплату",
                "payload": json.dumps({"cmd": "cancel_payment"}, ensure_ascii=False),
            },
            "color": "negative",
        }],
        garden_row(),
    ])
    send_message(
        f"💳 Ссылка для оплаты набора «{set_name}»:\n{url}\n\n"
        f"💡 Ссылка на оплату действует 1 час."
        + OFFERTA_TEXT,
        keyboard=payment_kb,
        skip_auto_buttons=True,
    )


def handle_cancel_payment(user, db, send_message):
    from models import PaymentOrder
    from bot.fsm import IDLE

    sd = json.loads(user.state_data or "{}")
    has_pending_email = any(k in sd for k in ("_pending_buy_set_id", "_partial_set_id"))
    for k in ("_pending_buy_set_id", "_pending_quantity", "_pending_amount",
              "_pending_price_per_pin", "_partial_set_id", "_partial_quantity",
              "_partial_amount", "_partial_price_per_pin"):
        sd.pop(k, None)
    order_id = sd.pop("_payment_order_id", None)

    if not order_id:
        if has_pending_email:
            user.state = IDLE
            user.state_data = json.dumps(sd, ensure_ascii=False)
            db.commit()
            send_message("✅ Ввод email отменён. Если передумаешь — выбери набор заново.")
        else:
            send_message("❌ Нет активного заказа для отмены.")
            user.state_data = json.dumps(sd, ensure_ascii=False)
            db.commit()
        return

    order = db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()
    if not order:
        user.state = IDLE
        send_message("❌ Заказ не найден.")
        user.state_data = json.dumps(sd, ensure_ascii=False)
        db.commit()
        return

    if order.status != "pending":
        user.state = IDLE
        send_message(f"❌ Заказ уже {order.status}, отмена невозможна.")
        user.state_data = json.dumps(sd, ensure_ascii=False)
        db.commit()
        return

    order.status = "cancelled"
    user.state = IDLE
    user.state_data = json.dumps(sd, ensure_ascii=False)
    db.commit()

    send_message("✅ Заказ отменён. Если передумаешь, можешь создать новый.")
