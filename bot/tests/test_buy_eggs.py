from datetime import datetime
from models import User, DragonSet, PaymentOrder, Dragon, PricingConfig
from bot.handlers.buy_eggs import handle_buy_eggs, handle_buy_set, handle_partial_confirm, handle_receipt_email, handle_cancel_payment, handle_open_payment


def _make_user(db, vk_id=1, state="idle", state_data="{}"):
    u = User(vk_id=vk_id, state=state, state_data=state_data)
    db.add(u)
    db.commit()
    return u


def _make_set(db, name="Стартовый", quantity=3, discount=0, donor_discount=0, sort_order=0):
    s = DragonSet(name=name, quantity=quantity, discount_percent=discount,
                  donor_discount_percent=donor_discount, is_active=True, sort_order=sort_order)
    db.add(s)
    db.commit()
    return s


def test_buy_eggs_no_packs(db):
    u = _make_user(db)
    msgs = []
    handle_buy_eggs(u, db, lambda m, **k: msgs.append(m))
    assert "нет доступных" in msgs[0].lower()


def test_buy_eggs_shows_packs(db):
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3, discount=0)
    msgs = []
    kbs = []

    def send(m, keyboard=None, **k):
        msgs.append(m)
        kbs.append(keyboard)

    handle_buy_eggs(u, db, send)
    joined = " ".join(msgs)
    assert "Стартовый" in joined
    assert "3 шт." in joined
    assert kbs[0] is not None
    assert "buy_set" in kbs[0]


def test_buy_eggs_shows_donor_discount(db, monkeypatch):
    monkeypatch.setattr("services.payment_service.is_donor", lambda vk_id, db: True)
    u = _make_user(db)
    s = _make_set(db, name="Премиум", quantity=5, discount=10, donor_discount=30)
    msgs = []

    def send(m, keyboard=None, **k):
        msgs.append(m)

    handle_buy_eggs(u, db, send)
    joined = " ".join(msgs)
    assert "Премиум" in joined
    assert "дона" in joined.lower()


def test_buy_set_asks_email(db):
    from bot.fsm import AWAIT_RECEIPT_EMAIL
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3)

    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    for i in range(1, 6):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()

    msgs = []
    handle_buy_set(u, s.id, db, lambda m, **k: msgs.append(m))
    assert any("email" in m.lower() for m in msgs)
    assert u.state == AWAIT_RECEIPT_EMAIL
    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order is None


def test_buy_set_creates_order_after_email(db):
    from bot.fsm import AWAIT_RECEIPT_EMAIL, IDLE
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3)

    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    for i in range(1, 6):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()

    handle_buy_set(u, s.id, db, lambda m, **k: None)
    assert u.state == AWAIT_RECEIPT_EMAIL

    msgs = []
    kbs = []
    def send(m, keyboard=None, **k):
        msgs.append(m)
        kbs.append(keyboard)

    handle_receipt_email(u, "player@example.com", db, send)
    msg = msgs[0]
    assert "Стартовый" in msg
    assert "3 шт." in msg
    assert "player@example.com" in msg
    assert "payment" in kbs[0] or "Оплат" in kbs[0]
    assert u.state == IDLE

    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order is not None
    assert order.status == "pending"
    assert order.set_id == s.id
    assert order.quantity == 3
    assert order.receipt_email == "player@example.com"


def test_buy_set_pending_order_reuses(db):
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3)

    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    existing = PaymentOrder(vk_id=u.vk_id, set_id=s.id, amount_rub=30000,
                            quantity=3, price_per_pin=10000, status="pending",
                            dragon_ids="[]", created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    db.add(existing)
    db.commit()

    msgs = []
    kbs = []

    def send(m, keyboard=None, **k):
        msgs.append(m)
        kbs.append(keyboard)

    handle_buy_set(u, s.id, db, send)
    msg = msgs[0]
    assert "неоплаченный" in msg.lower()
    assert kbs[0] is not None

    orders = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).all()
    assert len(orders) == 1


def test_buy_set_inactive(db):
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3)
    s.is_active = False
    db.commit()

    msgs = []
    handle_buy_set(u, s.id, db, lambda m, **k: msgs.append(m))
    assert "не найден" in msgs[0].lower()


def test_buy_set_no_dragons_available(db, monkeypatch):
    monkeypatch.setattr("services.payment_service.count_available", lambda vk_id, db: 0)
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3)

    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    db.commit()

    msgs = []
    handle_buy_set(u, s.id, db, lambda m, **k: msgs.append(m))
    assert "куплены" in msgs[0].lower()


def test_buy_set_partial_offer(db):
    u = _make_user(db)
    s = _make_set(db, name="Большой", quantity=5)

    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    for i in range(1, 5):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()

    msgs = []
    handle_buy_set(u, s.id, db, lambda m, **k: msgs.append(m))
    msg = msgs[0]
    assert "Доступно" in msg
    import json
    sd = json.loads(u.state_data or "{}")
    assert sd.get("_partial_set_id") == s.id


def test_partial_confirm_asks_email(db):
    from bot.fsm import AWAIT_RECEIPT_EMAIL
    import json
    u = _make_user(db, vk_id=5, state_data=json.dumps({
        "_partial_set_id": 1, "_partial_quantity": 2, "_partial_amount": 20000
    }))
    s = _make_set(db, name="Стартовый", quantity=5)
    s.id = 1
    db.commit()

    msgs = []
    handle_partial_confirm(u, db, lambda m, **k: msgs.append(m))
    assert any("email" in m.lower() for m in msgs)
    assert u.state == AWAIT_RECEIPT_EMAIL
    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order is None


def test_partial_confirm_creates_order_after_email(db):
    import json
    u = _make_user(db, vk_id=5, state_data=json.dumps({
        "_partial_set_id": 1, "_partial_quantity": 2, "_partial_amount": 20000
    }))
    s = _make_set(db, name="Стартовый", quantity=5)
    s.id = 1
    db.commit()

    handle_partial_confirm(u, db, lambda m, **k: None)

    msgs = []
    kbs = []
    def send(m, keyboard=None, **k):
        msgs.append(m)
        kbs.append(keyboard)

    handle_receipt_email(u, "partial@example.com", db, send)
    msg = msgs[0]
    assert "Стартовый" in msg
    assert "2 шт." in msg
    assert kbs[0] is not None

    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order is not None
    assert order.quantity == 2
    assert order.amount_rub == 20000
    assert order.receipt_email == "partial@example.com"

    sd = json.loads(u.state_data or "{}")
    assert "_pending_buy_set_id" not in sd


def test_partial_confirm_no_data(db):
    u = _make_user(db)
    msgs = []
    handle_partial_confirm(u, db, lambda m, **k: msgs.append(m))
    assert "не удалось" in msgs[0].lower()


def test_buy_set_not_found(db):
    u = _make_user(db)
    msgs = []
    handle_buy_set(u, 999, db, lambda m, **k: msgs.append(m))
    assert "не найден" in msgs[0].lower()


def test_buy_set_auto_cancels_expired_pending(db):
    from datetime import timedelta
    u = _make_user(db, vk_id=50)
    s = _make_set(db, name="Стартовый", quantity=3)
    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    for i in range(1, 6):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()

    old_str = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    existing = PaymentOrder(
        vk_id=u.vk_id, set_id=s.id, amount_rub=30000, quantity=3,
        price_per_pin=10000, status="pending", dragon_ids="[]",
        created_at=old_str,
    )
    db.add(existing)
    db.commit()

    msgs = []
    handle_buy_set(u, s.id, db, lambda m, **k: msgs.append(m))

    db.refresh(existing)
    assert existing.status == "cancelled"
    assert "Стартовый" in msgs[0]


def test_cancel_payment_cancels_order(db):
    import json
    u = _make_user(db, vk_id=60, state_data=json.dumps({"_payment_order_id": 1}))
    s = _make_set(db, name="Тестовый", quantity=3)
    order = PaymentOrder(
        id=1, vk_id=u.vk_id, set_id=s.id, amount_rub=30000, quantity=3,
        price_per_pin=10000, status="pending", dragon_ids="[]",
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(order)
    db.commit()

    from bot.handlers.buy_eggs import handle_cancel_payment
    msgs = []
    handle_cancel_payment(u, db, lambda m, **k: msgs.append(m))

    db.refresh(order)
    assert order.status == "cancelled"
    assert "отменён" in msgs[0].lower()

    sd = json.loads(u.state_data or "{}")
    assert "_payment_order_id" not in sd


def test_cancel_payment_no_order(db):
    u = _make_user(db)
    from bot.handlers.buy_eggs import handle_cancel_payment
    msgs = []
    handle_cancel_payment(u, db, lambda m, **k: msgs.append(m))
    assert "нет активного" in msgs[0].lower()


def test_cancel_payment_not_pending(db):
    import json
    u = _make_user(db, vk_id=70, state_data=json.dumps({"_payment_order_id": 2}))
    s = _make_set(db, name="Тестовый", quantity=3)
    order = PaymentOrder(
        id=2, vk_id=u.vk_id, set_id=s.id, amount_rub=30000, quantity=3,
        price_per_pin=10000, status="success", dragon_ids="[]",
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(order)
    db.commit()

    from bot.handlers.buy_eggs import handle_cancel_payment
    msgs = []
    handle_cancel_payment(u, db, lambda m, **k: msgs.append(m))

    db.refresh(order)
    assert order.status == "success"
    assert "уже" in msgs[0].lower()


# ─── Pay Gateway ───

def _gateway(monkeypatch, info=None, raises=None):
    import config
    monkeypatch.setattr(config, "USE_PAY_GATEWAY", True)
    from services import pay_gateway_client
    calls = []

    def fake_create_order(**kwargs):
        calls.append(kwargs)
        if raises is not None:
            raise raises
        return info or {
            "transaction_id": "20260824-000001",
            "payment_url": "https://belovolovhome.ru/pay/20260824-000001",
        }

    monkeypatch.setattr(pay_gateway_client, "create_order", fake_create_order)
    return calls


def _make_buy_context(db, quantity=3):
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=quantity)
    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    for i in range(1, quantity + 3):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()
    return u, s


def test_buy_set_gateway_creates_gateway_order(db, monkeypatch):
    import json
    u, s = _make_buy_context(db)
    calls = _gateway(monkeypatch)

    handle_buy_set(u, s.id, db, lambda m, **k: None)
    msgs = []
    handle_receipt_email(u, "buyer@example.com", db, lambda m, **k: msgs.append(m))

    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order is not None
    assert order.status == "pending"
    assert order.provider == "gateway"
    assert order.gateway_txn_id == "20260824-000001"
    assert calls[0]["vk_id"] == u.vk_id
    assert calls[0]["amount_kop"] == order.amount_rub
    assert calls[0]["receipt_email"] == "buyer@example.com"
    assert "Набор цифровых товаров" in calls[0]["description"]
    sd = json.loads(u.state_data or "{}")
    assert sd["_payment_order_id"] == order.id
    assert sd["_payment_url"] == "https://belovolovhome.ru/pay/20260824-000001"
    assert "Стартовый" in msgs[0]


def test_buy_set_gateway_failure_fails_order(db, monkeypatch):
    import json
    from services.pay_gateway_client import PayGatewayError
    u, s = _make_buy_context(db)
    _gateway(monkeypatch, raises=PayGatewayError("http 500: boom"))

    handle_buy_set(u, s.id, db, lambda m, **k: None)
    msgs = []
    handle_receipt_email(u, "buyer@example.com", db, lambda m, **k: msgs.append(m))

    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order.status == "failed"
    assert order.gateway_txn_id is None
    assert "недоступна" in msgs[0].lower()
    sd = json.loads(u.state_data or "{}")
    assert "_payment_order_id" not in sd


def test_buy_set_gateway_blocked_fails_order(db, monkeypatch):
    from services.pay_gateway_client import PayGatewayBlocked
    u, s = _make_buy_context(db)
    _gateway(monkeypatch, raises=PayGatewayBlocked("test_blocked"))

    handle_buy_set(u, s.id, db, lambda m, **k: None)
    msgs = []
    handle_receipt_email(u, "buyer@example.com", db, lambda m, **k: msgs.append(m))

    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order.status == "failed"
    assert "недоступна" in msgs[0].lower()


def test_open_payment_gateway_url(db, monkeypatch):
    u, s = _make_buy_context(db)
    _gateway(monkeypatch)
    handle_buy_set(u, s.id, db, lambda m, **k: None)
    handle_receipt_email(u, "buyer@example.com", db, lambda m, **k: None)

    msgs = []
    handle_open_payment(u, db, lambda m, **k: msgs.append(m))
    assert "https://belovolovhome.ru/pay/20260824-000001" in msgs[0]


def test_open_payment_gateway_url_fallback_without_stored(db, monkeypatch):
    import json
    import config
    monkeypatch.setattr(config, "PAY_GATEWAY_URL", "https://belovolovhome.ru/pay")
    u = _make_user(db, state_data=json.dumps({"_payment_order_id": 5}))
    s = _make_set(db, name="Стартовый", quantity=1)
    order = PaymentOrder(
        id=5, vk_id=u.vk_id, set_id=s.id, amount_rub=9500, quantity=1,
        price_per_pin=9500, status="pending", dragon_ids="[]",
        gateway_txn_id="20260824-000777", provider="gateway",
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(order)
    db.commit()

    msgs = []
    handle_open_payment(u, db, lambda m, **k: msgs.append(m))
    assert "https://belovolovhome.ru/pay/20260824-000777" in msgs[0]


def test_open_payment_old_path_url(db):
    u, s = _make_buy_context(db)
    handle_buy_set(u, s.id, db, lambda m, **k: None)
    handle_receipt_email(u, "buyer@example.com", db, lambda m, **k: None)
    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order.provider == "moneta"

    msgs = []
    handle_open_payment(u, db, lambda m, **k: msgs.append(m))
    assert f"/api/payment/pay/{order.id}" in msgs[0]


def test_open_payment_failed_gateway_order(db):
    import json
    u = _make_user(db, state_data=json.dumps({"_payment_order_id": 6}))
    s = _make_set(db, name="Стартовый", quantity=1)
    order = PaymentOrder(
        id=6, vk_id=u.vk_id, set_id=s.id, amount_rub=9500, quantity=1,
        price_per_pin=9500, status="failed", dragon_ids="[]",
        gateway_txn_id=None, provider="gateway",
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(order)
    db.commit()

    msgs = []
    handle_open_payment(u, db, lambda m, **k: msgs.append(m))
    assert "failed" in msgs[0]


# ─── Receipt email validation ───

def test_receipt_email_invalid_reprompts(db):
    from bot.fsm import AWAIT_RECEIPT_EMAIL
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3)
    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    for i in range(1, 6):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()

    handle_buy_set(u, s.id, db, lambda m, **k: None)
    assert u.state == AWAIT_RECEIPT_EMAIL

    msgs = []
    handle_receipt_email(u, "not-an-email", db, lambda m, **k: msgs.append(m))
    assert "не email" in msgs[0].lower() or "ещё раз" in msgs[0].lower()
    assert u.state == AWAIT_RECEIPT_EMAIL
    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order is None


def test_receipt_email_no_data_returns_idle(db):
    from bot.fsm import AWAIT_RECEIPT_EMAIL, IDLE
    u = _make_user(db, state=AWAIT_RECEIPT_EMAIL, state_data="{}")
    msgs = []
    handle_receipt_email(u, "good@example.com", db, lambda m, **k: msgs.append(m))
    assert u.state == IDLE
    assert "не удалось" in msgs[0].lower()


def test_cancel_payment_from_email_state_resets(db):
    from bot.fsm import AWAIT_RECEIPT_EMAIL, IDLE
    import json
    u = _make_user(db, state=AWAIT_RECEIPT_EMAIL, state_data=json.dumps({"_pending_buy_set_id": 1}))
    msgs = []
    handle_cancel_payment(u, db, lambda m, **k: msgs.append(m))
    assert u.state == IDLE
    assert "отменён" in msgs[0].lower() or "отмен" in msgs[0].lower()


def test_cancel_email_step_ignores_old_success_order(db):
    from bot.fsm import AWAIT_RECEIPT_EMAIL, IDLE
    import json
    s = _make_set(db, name="Стартовый", quantity=3)
    old_order = PaymentOrder(
        id=777, vk_id=99, set_id=s.id, amount_rub=30000, quantity=3,
        price_per_pin=10000, status="success", dragon_ids="[]",
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(old_order)
    db.commit()
    u = _make_user(db, vk_id=99, state=AWAIT_RECEIPT_EMAIL,
                   state_data=json.dumps({"_pending_buy_set_id": s.id, "_payment_order_id": 777}))
    msgs = []
    handle_cancel_payment(u, db, lambda m, **k: msgs.append(m))
    assert u.state == IDLE
    assert "email" in msgs[0].lower()
    db.refresh(old_order)
    assert old_order.status == "success"
