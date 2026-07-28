from datetime import datetime
from models import Dragon, DragonReservation, User, UserDragon
from bot.services.pin_service import activate_pin, validate_pin_code, activate_pin_silently, activate_all_reservations


def test_activate_pin_updates_reservation(db):
    dragon = Dragon(name="ResDragon", rarity=2, steps_count=3, is_active=True, pin_code="TEST1")
    db.add(dragon)
    db.flush()

    reservation = DragonReservation(
        vk_url="https://vk.ru/id123",
        vk_user_id=None,
        dragon_id=dragon.id,
        is_activated=False,
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(reservation)
    db.commit()

    user = User(vk_id=123, state="idle")
    db.add(user)
    db.commit()

    result = activate_pin(db, 123, dragon)
    assert result is True

    db.refresh(reservation)
    assert reservation.is_activated is True
    assert reservation.vk_user_id == 123
    assert reservation.activated_at is not None


def test_activate_pin_updates_reservation_by_dragon_only(db):
    dragon = Dragon(name="Res2", rarity=1, steps_count=2, is_active=True, pin_code="TEST2")
    db.add(dragon)
    db.flush()

    reservation = DragonReservation(
        vk_url="https://vk.ru/eugenibelovolov",
        vk_user_id=None,
        dragon_id=dragon.id,
        is_activated=False,
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        updated_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(reservation)
    db.commit()

    user = User(vk_id=456, state="idle")
    db.add(user)
    db.commit()

    result = activate_pin(db, 456, dragon)
    assert result is True

    db.refresh(reservation)
    assert reservation.is_activated is True
    assert reservation.vk_user_id == 456


def test_activate_pin_no_reservation_ok(db):
    dragon = Dragon(name="NoRes", rarity=1, steps_count=2, is_active=True, pin_code="NORES")
    db.add(dragon)
    db.commit()

    user = User(vk_id=789, state="idle")
    db.add(user)
    db.commit()

    result = activate_pin(db, 789, dragon)
    assert result is True


def test_validate_pin_code_works(db):
    dragon = Dragon(name="PinDragon", rarity=2, steps_count=3, is_active=True, pin_code="VPIN1")
    db.add(dragon)
    db.commit()

    result = validate_pin_code(db, "VPIN1")
    assert result is not None
    assert result.name == "PinDragon"

    result = validate_pin_code(db, "WRONG")
    assert result is None


def test_activate_pin_duplicate_returns_false(db):
    dragon = Dragon(name="Dup", rarity=1, steps_count=2, is_active=True, pin_code="DUP01")
    db.add(dragon)
    db.commit()

    user = User(vk_id=111, state="idle")
    db.add(user)
    db.commit()

    assert activate_pin(db, 111, dragon) is True
    assert activate_pin(db, 111, dragon) is False


def _make_dragon(db, name, pin):
    dragon = Dragon(name=name, rarity=1, steps_count=2, is_active=True, pin_code=pin)
    db.add(dragon)
    db.flush()
    return dragon


def _make_reservation(db, dragon_id, vk_id):
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    r = DragonReservation(
        vk_url=f"https://vk.ru/id{vk_id}",
        vk_user_id=vk_id,
        dragon_id=dragon_id,
        is_activated=False,
        created_at=now,
        updated_at=now,
    )
    db.add(r)
    return r


def test_activate_all_reservations_activates_all(db):
    user = User(vk_id=200, state="idle")
    db.add(user)
    db.commit()

    dragons = [_make_dragon(db, f"Batch{i}", f"BTCH{i}") for i in range(5)]
    db.commit()

    for d in dragons:
        _make_reservation(db, d.id, 200)
    db.commit()

    activated, total = activate_all_reservations(db, 200)
    assert activated == 5
    assert total == 5

    for d in dragons:
        ud = db.query(UserDragon).filter(
            UserDragon.user_id == 200, UserDragon.dragon_id == d.id
        ).first()
        assert ud is not None


def test_activate_all_skips_missing_dragon(db):
    user = User(vk_id=201, state="idle")
    db.add(user)
    db.commit()

    dragon = _make_dragon(db, "Valid", "VLID1")
    db.commit()

    _make_reservation(db, dragon.id, 201)
    r2 = _make_reservation(db, 99999, 201)
    db.commit()

    activated, total = activate_all_reservations(db, 201)
    assert activated == 1
    assert total == 2


def test_other_user_reservation_not_stolen_on_activation(db):
    dragon = _make_dragon(db, "Shared", "SHRD1")
    db.commit()

    res_a = _make_reservation(db, dragon.id, 300)
    res_b = _make_reservation(db, dragon.id, 400)
    db.commit()

    user_a = User(vk_id=300, state="idle")
    user_b = User(vk_id=400, state="idle")
    db.add(user_a)
    db.add(user_b)
    db.commit()

    result_a = activate_pin(db, 300, dragon)
    assert result_a is True

    db.refresh(res_a)
    assert res_a.is_activated is True
    assert res_a.vk_user_id == 300

    db.refresh(res_b)
    assert res_b.is_activated is False
    assert res_b.vk_user_id == 400


def test_other_user_reservation_not_stolen_silently(db):
    dragon = _make_dragon(db, "Shared2", "SHRD2")
    db.commit()

    res_a = _make_reservation(db, dragon.id, 500)
    db.commit()

    result_b = activate_pin_silently(db, 600, dragon)
    assert result_b is True

    db.refresh(res_a)
    assert res_a.is_activated is False
    assert res_a.vk_user_id == 500


def test_null_owner_reservation_fallback_still_works(db):
    dragon = _make_dragon(db, "NullDrag", "NULL1")
    db.commit()

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    reservation = DragonReservation(
        vk_url="https://vk.ru/id700",
        vk_user_id=None,
        dragon_id=dragon.id,
        is_activated=False,
        created_at=now,
        updated_at=now,
    )
    db.add(reservation)
    db.commit()

    user = User(vk_id=700, state="idle")
    db.add(user)
    db.commit()

    result = activate_pin(db, 700, dragon)
    assert result is True

    db.refresh(reservation)
    assert reservation.is_activated is True
    assert reservation.vk_user_id == 700


def test_own_reservation_prioritized_over_null_owner(db):
    dragon = _make_dragon(db, "PriorDrag", "PRIO1")
    db.commit()

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    null_res = DragonReservation(
        vk_url="https://vk.ru/id800",
        vk_user_id=None,
        dragon_id=dragon.id,
        is_activated=False,
        created_at=now,
        updated_at=now,
    )
    db.add(null_res)
    _make_reservation(db, dragon.id, 800)
    db.commit()

    user = User(vk_id=800, state="idle")
    db.add(user)
    db.commit()

    result = activate_pin(db, 800, dragon)
    assert result is True

    own = db.query(DragonReservation).filter(
        DragonReservation.dragon_id == dragon.id,
        DragonReservation.vk_user_id == 800,
    ).first()
    assert own is not None
    assert own.is_activated is True

    null = db.query(DragonReservation).filter(
        DragonReservation.dragon_id == dragon.id,
        DragonReservation.vk_user_id == None,
    ).first()
    assert null is not None
    assert null.is_activated is False
