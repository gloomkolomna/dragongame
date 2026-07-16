from datetime import datetime
from models import Dragon, DragonReservation, User, UserDragon, UserRewardPin, RewardConfig
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
