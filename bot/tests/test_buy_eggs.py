from models import User, DragonSet, PaymentOrder, Dragon, PricingConfig
from bot.handlers.buy_eggs import handle_buy_eggs, handle_buy_set, handle_partial_confirm


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


def test_buy_set_creates_order(db):
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3)

    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    for i in range(1, 6):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()

    msgs = []
    kbs = []

    def send(m, keyboard=None, **k):
        msgs.append(m)
        kbs.append(keyboard)

    handle_buy_set(u, s.id, db, send)
    msg = msgs[0]
    assert "Стартовый" in msg
    assert "3 шт." in msg
    assert kbs[0] is not None
    assert "payment" in kbs[0] or "Оплат" in kbs[0] or "auth.robokassa" in kbs[0]

    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order is not None
    assert order.status == "pending"
    assert order.set_id == s.id
    assert order.quantity == 3


def test_buy_set_pending_order_reuses(db):
    u = _make_user(db)
    s = _make_set(db, name="Стартовый", quantity=3)

    db.add(PricingConfig(id=1, base_price_per_dragon=10000))
    existing = PaymentOrder(vk_id=u.vk_id, set_id=s.id, amount_rub=30000,
                            quantity=3, price_per_pin=10000, status="pending",
                            dragon_ids="[]", created_at="2026-01-01T00:00:00")
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


def test_partial_confirm_creates_order(db):
    import json
    u = _make_user(db, vk_id=5, state_data=json.dumps({
        "_partial_set_id": 1, "_partial_quantity": 2, "_partial_amount": 20000
    }))
    s = _make_set(db, name="Стартовый", quantity=5)
    s.id = 1
    db.commit()

    msgs = []
    kbs = []

    def send(m, keyboard=None, **k):
        msgs.append(m)
        kbs.append(keyboard)

    handle_partial_confirm(u, db, send)
    msg = msgs[0]
    assert "частичный" in msg.lower()
    assert kbs[0] is not None

    order = db.query(PaymentOrder).filter(PaymentOrder.vk_id == u.vk_id).first()
    assert order is not None
    assert order.quantity == 2
    assert order.amount_rub == 20000

    sd = json.loads(u.state_data or "{}")
    assert "_partial_set_id" not in sd


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
