from datetime import datetime
from models import Dragon, DragonReservation, User, UserDragon
from bot.services.pin_service import activate_pin, validate_pin_code


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
