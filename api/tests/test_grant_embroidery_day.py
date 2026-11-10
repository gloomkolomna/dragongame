from models import Dragon, DragonReservation, User, UserDragon, UserRewardPin
from scripts.grant_embroidery_day import NOTES, SOURCE, grant_random_dragon, run


def _dragon(db, name="Огненный", pin="EGG01"):
    dragon = Dragon(
        name=name,
        rarity=1,
        steps_count=1,
        pin_code=pin,
        is_active=True,
        is_epic=False,
    )
    db.add(dragon)
    db.commit()
    db.refresh(dragon)
    return dragon


def _user(db, vk_id=100):
    user = User(vk_id=vk_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_dry_run_selects_dragon_without_writing(db):
    user = _user(db)
    dragon = _dragon(db)

    status, selected = grant_random_dragon(db, user)

    assert status == "planned"
    assert selected.id == dragon.id
    assert db.query(DragonReservation).count() == 0
    assert db.query(UserRewardPin).count() == 0


def test_apply_creates_reservation_and_reward_pin(db):
    user = _user(db)
    dragon = _dragon(db)

    status, selected = grant_random_dragon(db, user, apply=True)

    assert status == "created"
    assert selected.id == dragon.id
    reservation = db.query(DragonReservation).one()
    assert reservation.vk_user_id == user.vk_id
    assert reservation.dragon_id == dragon.id
    assert reservation.source == SOURCE
    assert reservation.external_reward_id == f"embroidery_day:2026:{user.vk_id}"
    assert reservation.notes == NOTES
    assert reservation.is_activated is False
    pin = db.query(UserRewardPin).one()
    assert pin.user_id == user.vk_id
    assert pin.dragon_id == dragon.id
    assert pin.pin_code == dragon.pin_code
    assert pin.source == SOURCE
    assert pin.external_reward_id == reservation.external_reward_id
    assert pin.activated is False


def test_repeated_apply_does_not_create_duplicates(db):
    user = _user(db)
    _dragon(db)

    first_status, _ = grant_random_dragon(db, user, apply=True)
    second_status, _ = grant_random_dragon(db, user, apply=True)

    assert first_status == "created"
    assert second_status == "existing"
    assert db.query(DragonReservation).count() == 1
    assert db.query(UserRewardPin).count() == 1


def test_selection_excludes_owned_and_reserved_dragons(db):
    user = _user(db)
    owned = _dragon(db, "Уже получен", "EGG01")
    reserved = _dragon(db, "Уже забронирован", "EGG02")
    available = _dragon(db, "Доступный", "EGG03")
    db.add(UserDragon(user_id=user.vk_id, dragon_id=owned.id, completed_at=""))
    db.add(DragonReservation(
        vk_url=f"https://vk.ru/id{user.vk_id}",
        vk_user_id=user.vk_id,
        dragon_id=reserved.id,
        is_activated=False,
    ))
    db.commit()

    status, selected = grant_random_dragon(db, user, apply=True)

    assert status == "created"
    assert selected.id == available.id


def test_user_without_available_dragons_is_skipped(db):
    user = _user(db)
    dragon = _dragon(db)
    db.add(UserDragon(user_id=user.vk_id, dragon_id=dragon.id, completed_at=""))
    db.commit()

    status, selected = grant_random_dragon(db, user, apply=True)

    assert status == "unavailable"
    assert selected is None
    assert db.query(DragonReservation).count() == 0
    assert db.query(UserRewardPin).count() == 0


def test_run_processes_every_user(db):
    first = _user(db, 100)
    second = _user(db, 200)
    dragon = _dragon(db)

    counts = run(db, apply=True)

    assert counts["created"] == 2
    assert counts["failed"] == 0
    reservations = db.query(DragonReservation).all()
    assert {r.vk_user_id for r in reservations} == {first.vk_id, second.vk_id}
    assert all(r.dragon_id == dragon.id for r in reservations)
    assert db.query(UserRewardPin).count() == 2
