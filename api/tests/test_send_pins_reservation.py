from datetime import datetime
from models import Dragon, DragonReservation
from routes.payment import _send_pins


def _dragon(db, name, pin):
    d = Dragon(name=name, egg_type="egg", rarity=1, steps_count=1,
               pin_code=pin, is_active=True)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def test_send_pins_creates_reservation_when_other_user_has_inactive(db, monkeypatch):
    monkeypatch.setattr("config.VK_GROUP_TOKEN", "")

    d = _dragon(db, "SharedEgg", "57F0G")

    other_res = DragonReservation(
        vk_url="https://vk.ru/id999",
        vk_user_id=999,
        vk_name="Other Buyer",
        dragon_id=d.id,
        is_activated=False,
        notes="Покупка через Robokassa",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(other_res)
    db.commit()

    _send_pins(42, [d], db)

    buyer_res = db.query(DragonReservation).filter(
        DragonReservation.dragon_id == d.id,
        DragonReservation.vk_user_id == 42,
        DragonReservation.is_activated == False,
    ).first()
    assert buyer_res is not None
    assert buyer_res.notes == "Покупка через Robokassa"

    db.refresh(other_res)
    assert other_res.vk_user_id == 999
    assert other_res.is_activated is False


def test_send_pins_batch_creates_reservation_per_egg_even_if_all_shared(db, monkeypatch):
    monkeypatch.setattr("config.VK_GROUP_TOKEN", "")

    dragons = [_dragon(db, f"Egg{i}", f"PIN0{i}") for i in range(13)]
    db.commit()

    for d in dragons:
        db.add(DragonReservation(
            vk_url="https://vk.ru/id777",
            vk_user_id=777,
            dragon_id=d.id,
            is_activated=False,
            created_at=_now(),
            updated_at=_now(),
        ))
    db.commit()

    _send_pins(42, dragons, db)

    buyer_reservations = db.query(DragonReservation).filter(
        DragonReservation.vk_user_id == 42,
        DragonReservation.is_activated == False,
    ).all()
    assert len(buyer_reservations) == 13
    assert {r.dragon_id for r in buyer_reservations} == {d.id for d in dragons}


def test_send_pins_does_not_duplicate_own_reservation(db, monkeypatch):
    monkeypatch.setattr("config.VK_GROUP_TOKEN", "")

    d = _dragon(db, "Solo", "SOLO1")

    own = DragonReservation(
        vk_url="https://vk.ru/id42",
        vk_user_id=42,
        dragon_id=d.id,
        is_activated=False,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(own)
    db.commit()

    _send_pins(42, [d], db)

    own_reservations = db.query(DragonReservation).filter(
        DragonReservation.dragon_id == d.id,
        DragonReservation.vk_user_id == 42,
        DragonReservation.is_activated == False,
    ).all()
    assert len(own_reservations) == 1
