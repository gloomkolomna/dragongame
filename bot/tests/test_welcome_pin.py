import json
from datetime import datetime
from unittest.mock import patch

from models import Dragon, DonorCache, User, UserDragon, UserRewardPin, DragonReservation
from bot.services.welcome_service import ensure_donor_welcome_pin


def _make_dragon(db, name, **kw):
    defaults = dict(name=name, rarity=1, steps_count=2, is_active=True, pin_code=name)
    defaults.update(kw)
    d = Dragon(**defaults)
    db.add(d)
    db.flush()
    return d


def _make_donor(db, vk_id):
    db.add(DonorCache(vk_id=vk_id, is_don=True, don_since=datetime.now().isoformat(), updated_at="", last_synced_at=""))
    db.commit()


def test_welcome_issued_to_donor(db):
    d1 = _make_dragon(db, "AAAA1")
    _make_donor(db, 100)

    result = ensure_donor_welcome_pin(db, 100)

    assert result is True
    pin = db.query(UserRewardPin).filter(UserRewardPin.user_id == 100).one()
    assert pin.config_id is None
    assert pin.dragon_id == d1.id
    res = db.query(DragonReservation).filter(DragonReservation.vk_user_id == 100).one()
    assert res.dragon_id == d1.id
    assert res.is_activated is False


def test_welcome_idempotent(db):
    _make_dragon(db, "AAAA1")
    _make_donor(db, 100)

    assert ensure_donor_welcome_pin(db, 100) is True
    assert ensure_donor_welcome_pin(db, 100) is False

    pins = db.query(UserRewardPin).filter(UserRewardPin.user_id == 100).all()
    assert len(pins) == 1
    reservations = db.query(DragonReservation).filter(DragonReservation.vk_user_id == 100).all()
    assert len(reservations) == 1


def test_welcome_not_issued_to_non_donor(db):
    _make_dragon(db, "AAAA1")

    assert ensure_donor_welcome_pin(db, 100) is False
    assert db.query(UserRewardPin).count() == 0
    assert db.query(DragonReservation).count() == 0


def test_welcome_excludes_epic_inactive_no_pin(db):
    _make_dragon(db, "EPIC1", is_epic=True)
    _make_dragon(db, "INACT1", is_active=False)
    _make_dragon(db, "", pin_code=None)
    _make_donor(db, 100)

    assert ensure_donor_welcome_pin(db, 100) is False
    assert db.query(UserRewardPin).count() == 0


def test_welcome_excludes_owned_dragons(db):
    d1 = _make_dragon(db, "AAAA1")
    _make_donor(db, 100)
    db.add(UserDragon(user_id=100, dragon_id=d1.id, completed_at=""))
    db.commit()

    assert ensure_donor_welcome_pin(db, 100) is False
    assert db.query(UserRewardPin).count() == 0


def test_welcome_excludes_own_reservations(db):
    d1 = _make_dragon(db, "AAAA1")
    _make_donor(db, 100)
    db.add(DragonReservation(
        vk_url="https://vk.ru/id100", vk_user_id=100, dragon_id=d1.id,
        is_activated=False, created_at="", updated_at="",
    ))
    db.commit()

    assert ensure_donor_welcome_pin(db, 100) is False
    pins = db.query(UserRewardPin).filter(UserRewardPin.user_id == 100).all()
    assert len(pins) == 0


def test_two_donors_can_get_same_dragon(db):
    d1 = _make_dragon(db, "AAAA1")
    _make_donor(db, 100)
    _make_donor(db, 200)

    assert ensure_donor_welcome_pin(db, 100) is True
    assert ensure_donor_welcome_pin(db, 200) is True

    pins100 = db.query(UserRewardPin).filter(UserRewardPin.user_id == 100).all()
    pins200 = db.query(UserRewardPin).filter(UserRewardPin.user_id == 200).all()
    assert len(pins100) == 1
    assert len(pins200) == 1
    assert pins100[0].dragon_id == d1.id
    assert pins200[0].dragon_id == d1.id

    res100 = db.query(DragonReservation).filter(DragonReservation.vk_user_id == 100).one()
    res200 = db.query(DragonReservation).filter(DragonReservation.vk_user_id == 200).one()
    assert res100.dragon_id == d1.id
    assert res200.dragon_id == d1.id


def test_post_intro_keyboard_donor_has_my_pins(db):
    from bot.handlers.intro import _post_intro_keyboard
    _make_donor(db, 100)

    kb = json.loads(_post_intro_keyboard(db, 100))
    labels = [b["action"]["label"] for r in kb["buttons"] for b in r]
    assert any("Мои PIN" in l for l in labels)


def test_post_intro_keyboard_non_donor_has_no_my_pins(db):
    from bot.handlers.intro import _post_intro_keyboard

    kb = json.loads(_post_intro_keyboard(db, 100))
    labels = [b["action"]["label"] for r in kb["buttons"] for b in r]
    assert not any("Мои PIN" in l for l in labels)


def test_get_or_create_user_issues_welcome_for_donor(db):
    from bot.services.user_service import get_or_create_user
    _make_dragon(db, "AAAA1")
    db.add(DonorCache(vk_id=500, is_don=True, don_since="", updated_at="", last_synced_at=""))
    db.commit()

    with patch("bot.services.donor_sync.sync_user"), \
         patch("config.VK_GROUP_TOKEN", ""):
        user = get_or_create_user(db, 500)

    assert user is not None
    pin = db.query(UserRewardPin).filter(UserRewardPin.user_id == 500).first()
    assert pin is not None
    assert pin.config_id is None
