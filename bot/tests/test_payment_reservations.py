import hashlib
from datetime import datetime
from urllib.parse import parse_qs, urlparse, unquote_plus, quote_plus
from models import Dragon, DragonReservation, User, UserDragon, UserRewardPin, RewardConfig, PaymentOrder, DragonSet
from api.services.payment_service import select_dragons, _available_dragons


def test_available_dragons_excludes_reserved(db):
    d1 = Dragon(name="D1", rarity=1, steps_count=2, is_active=True, pin_code="11111")
    d2 = Dragon(name="D2", rarity=2, steps_count=3, is_active=True, pin_code="22222")
    d3 = Dragon(name="D3", rarity=3, steps_count=4, is_active=True, pin_code="33333")
    db.add_all([d1, d2, d3])
    db.flush()

    reservation = DragonReservation(
        vk_url="https://vk.ru/id1", vk_user_id=1,
        dragon_id=d2.id, is_activated=False,
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(reservation)
    db.commit()

    user = User(vk_id=100, state="idle")
    db.add(user)
    db.commit()

    available = _available_dragons(100, db)
    available_ids = {d.id for d in available}
    assert d1.id in available_ids
    assert d2.id in available_ids
    assert d3.id in available_ids


def test_select_dragons_skips_reserved(db):
    d1 = Dragon(name="D1", rarity=1, steps_count=2, is_active=True, pin_code="11111")
    d2 = Dragon(name="D2", rarity=2, steps_count=3, is_active=True, pin_code="22222")
    db.add_all([d1, d2])
    db.flush()

    reservation = DragonReservation(
        vk_url="https://vk.ru/id1", vk_user_id=1,
        dragon_id=d2.id, is_activated=False,
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(reservation)
    db.commit()

    user = User(vk_id=1, state="idle")
    db.add(user)
    db.commit()

    result = select_dragons(1, 1, db)
    assert len(result) == 1
    assert result[0].id == d1.id


def test_other_user_can_get_reserved_dragon(db):
    d1 = Dragon(name="D1", rarity=1, steps_count=2, is_active=True, pin_code="11111")
    d2 = Dragon(name="D2", rarity=2, steps_count=3, is_active=True, pin_code="22222")
    db.add_all([d1, d2])
    db.flush()

    reservation = DragonReservation(
        vk_url="https://vk.ru/id1", vk_user_id=1,
        dragon_id=d2.id, is_activated=False,
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(reservation)
    db.commit()

    user = User(vk_id=999, state="idle")
    db.add(user)
    db.commit()

    available = _available_dragons(999, db)
    available_ids = {d.id for d in available}
    assert d2.id in available_ids

    result = select_dragons(999, 2, db)
    result_ids = {d.id for d in result}
    assert d1.id in result_ids
    assert d2.id in result_ids


def test_available_dragons_includes_activated_reservation(db):
    d1 = Dragon(name="D1", rarity=1, steps_count=2, is_active=True, pin_code="11111")
    db.add(d1)
    db.flush()

    reservation = DragonReservation(
        vk_url="https://vk.ru/id1",
        dragon_id=d1.id,
        is_activated=True,
        activated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(reservation)
    db.commit()

    user = User(vk_id=300, state="idle")
    db.add(user)
    db.commit()

    available = _available_dragons(300, db)
    available_ids = {d.id for d in available}
    assert d1.id in available_ids


def test_same_player_cant_get_own_reserved_via_payment(db):
    d1 = Dragon(name="D1", rarity=1, steps_count=2, is_active=True, pin_code="11111")
    d2 = Dragon(name="D2", rarity=2, steps_count=3, is_active=True, pin_code="22222")
    db.add_all([d1, d2])
    db.flush()

    reservation = DragonReservation(
        vk_url="https://vk.ru/id777",
        vk_user_id=777,
        dragon_id=d2.id,
        is_activated=False,
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(reservation)
    db.commit()

    user = User(vk_id=777, state="idle")
    db.add(user)
    db.commit()

    available = _available_dragons(777, db)
    available_ids = {d.id for d in available}
    assert d1.id in available_ids
    assert d2.id not in available_ids

    result = select_dragons(777, 1, db)
    assert len(result) == 1
    assert result[0].id == d1.id


def test_same_player_cant_get_own_reserved_via_rewards(db):
    d1 = Dragon(name="D1", rarity=1, steps_count=2, is_active=True, pin_code="11111")
    d2 = Dragon(name="D2", rarity=2, steps_count=3, is_active=True, pin_code="22222")
    db.add_all([d1, d2])
    db.flush()

    reservation = DragonReservation(
        vk_url="https://vk.ru/id888",
        vk_user_id=888,
        dragon_id=d2.id,
        is_activated=False,
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(reservation)
    db.commit()

    cfg = RewardConfig(
        user_type="regular", eggs_per_period=2, period_days=30,
        is_active=True, created_at="2026-01-01T00:00:00", updated_at="2026-01-01T00:00:00",
    )
    db.add(cfg)
    db.commit()

    user = User(vk_id=888, state="idle", registered_at="2026-01-01T00:00:00")
    db.add(user)
    db.commit()

    from bot.services.reward_service import _process_rewards
    import logging
    null_logger = logging.getLogger("null")
    null_logger.addHandler(logging.NullHandler())

    class FakeVk:
        def __init__(self):
            self.messages_sent = []
        def messages_send(self, user_id, message, random_id, keyboard=None, attachment=""):
            self.messages_sent.append({"user_id": user_id, "message": message})
            return {}

    fake_vk = FakeVk()
    _process_rewards(db, fake_vk, null_logger)

    pins = db.query(UserRewardPin).filter(UserRewardPin.user_id == 888).all()
    pin_dragon_ids = {p.dragon_id for p in pins}
    assert d2.id not in pin_dragon_ids
    assert len(pins) == 1
    assert pins[0].dragon_id == d1.id

    reservations = db.query(DragonReservation).filter(
        DragonReservation.vk_user_id == 888,
        DragonReservation.is_activated == False,
    ).all()
    assert len(reservations) == 2
    res_dragon_ids = {r.dragon_id for r in reservations}
    assert d1.id in res_dragon_ids
    assert d2.id in res_dragon_ids


def test_bot_payment_url_contains_receipt(db, monkeypatch):
    import config
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    monkeypatch.setattr(config, "ROBOKASSA_MERCHANT_LOGIN", "testlogin")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD1", "pass1")
    from bot.handlers.buy_eggs import _build_payment_url

    s = DragonSet(name="Test Set", quantity=3)
    db.add(s)
    db.commit()
    order = PaymentOrder(
        vk_id=123, set_id=s.id, amount_rub=28500, quantity=3,
        price_per_pin=9500, status="pending",
    )
    db.add(order)
    db.commit()

    url = _build_payment_url(order, 123, "Набор «Test Set»")

    assert "Receipt=" in url
    assert "tax" in url and "none" in url


def test_bot_payment_url_receipt_in_signature(db, monkeypatch):
    import config
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    monkeypatch.setattr(config, "ROBOKASSA_MERCHANT_LOGIN", "bestiary")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD1", "sec1")
    from bot.handlers.buy_eggs import _build_payment_url

    s = DragonSet(name="Test", quantity=2)
    db.add(s)
    db.commit()
    order = PaymentOrder(
        vk_id=10, set_id=s.id, amount_rub=19000, quantity=2,
        price_per_pin=9500, status="pending",
    )
    db.add(order)
    db.commit()

    url = _build_payment_url(order, 10, "Набор «Test»")
    qs = parse_qs(urlparse(url).query)
    receipt_raw = unquote_plus(qs["Receipt"][0])
    out_sum = qs["OutSum"][0]
    inv_id = qs["InvId"][0]
    login = qs["MerchantLogin"][0]
    receipt_encoded = quote_plus(receipt_raw, safe="")
    expected = hashlib.md5(
        f"{login}:{out_sum}:{inv_id}:{receipt_encoded}:sec1:Shp_vk_id=10".encode("utf-8")
    ).hexdigest()
    assert qs["SignatureValue"][0] == expected


def test_bot_payment_url_has_istest_in_test_mode(db, monkeypatch):
    import config
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    monkeypatch.setattr(config, "ROBOKASSA_MERCHANT_LOGIN", "testlogin")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD1", "testpass1")
    from bot.handlers.buy_eggs import _build_payment_url

    s = DragonSet(name="Test", quantity=1)
    db.add(s)
    db.commit()
    order = PaymentOrder(
        vk_id=7, set_id=s.id, amount_rub=9500, quantity=1,
        price_per_pin=9500, status="pending",
    )
    db.add(order)
    db.commit()

    url = _build_payment_url(order, 7, "Test")
    assert "IsTest=1" in url


def test_bot_payment_url_no_istest_in_prod(db, monkeypatch):
    import config
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    monkeypatch.setattr(config, "ROBOKASSA_MERCHANT_LOGIN", "testlogin")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD1", "pass1")
    from bot.handlers.buy_eggs import _build_payment_url

    s = DragonSet(name="Test", quantity=1)
    db.add(s)
    db.commit()
    order = PaymentOrder(
        vk_id=8, set_id=s.id, amount_rub=9500, quantity=1,
        price_per_pin=9500, status="pending",
    )
    db.add(order)
    db.commit()

    url = _build_payment_url(order, 8, "Test")
    assert "IsTest" not in url
