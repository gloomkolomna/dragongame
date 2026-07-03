from datetime import datetime, timedelta
import logging
from unittest.mock import MagicMock
from models import Dragon, DragonStep, User, UserDragon, UserProgress


def _setup(db):
    d = Dragon(name="Test", rarity=2, steps_count=3, is_active=True)
    db.add(d)
    db.flush()
    for i in range(1, 4):
        db.add(DragonStep(
            dragon_id=d.id, step_number=i,
            magic_action=f"A{i}",
        ))
    u = User(vk_id=1, state="grow_step_2", current_dragon_id=d.id, current_step=2)
    db.add(u)
    past = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
    ud = UserDragon(
        user_id=1, dragon_id=d.id,
        next_step_available_at=past,
        timeout_notified=False,
    )
    db.add(ud)
    db.commit()
    return d, u


def test_check_expired_sends_notification(db):
    from bot.scheduler import _check_expired

    d, u = _setup(db)
    vk_mock = MagicMock()
    logger = logging.getLogger("test")

    _check_expired(db, vk_mock, logger)

    assert vk_mock.messages.send.called


def test_check_expired_marks_notified(db):
    from bot.scheduler import _check_expired

    d, u = _setup(db)
    vk_mock = MagicMock()
    logger = logging.getLogger("test")

    _check_expired(db, vk_mock, logger)

    ud = db.query(UserDragon).filter(
        UserDragon.user_id == 1, UserDragon.dragon_id == d.id
    ).first()
    assert ud.timeout_notified is True


def test_check_expired_skips_notified(db):
    from bot.scheduler import _check_expired

    d, u = _setup(db)
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == 1, UserDragon.dragon_id == d.id
    ).first()
    ud.timeout_notified = True
    db.commit()

    vk_mock = MagicMock()
    _check_expired(db, vk_mock, logging.getLogger("test"))

    assert not vk_mock.messages.send.called


def test_check_expired_skips_future_timeout(db):
    from bot.scheduler import _check_expired

    d, u = _setup(db)
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == 1, UserDragon.dragon_id == d.id
    ).first()
    future = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%S")
    ud.next_step_available_at = future
    db.commit()

    vk_mock = MagicMock()
    _check_expired(db, vk_mock, logging.getLogger("test"))

    assert not vk_mock.messages.send.called


def test_check_expired_sends_button_for_other_dragon(db):
    from bot.scheduler import _check_expired

    d, u = _setup(db)
    # User is on a DIFFERENT dragon
    other = Dragon(name="Other", rarity=1, steps_count=1, is_active=True)
    db.add(other)
    db.flush()
    u.current_dragon_id = other.id
    db.commit()

    vk_mock = MagicMock()
    _check_expired(db, vk_mock, logging.getLogger("test"))

    assert vk_mock.messages.send.called
    call_kwargs = vk_mock.messages.send.call_args[1]
    assert "Перейти к выращиванию" in call_kwargs.get("message", "") or \
           "Перейти к выращиванию" in call_kwargs.get("keyboard", "")


def test_check_expired_fires_after_time_passes(db):
    from bot.scheduler import _check_expired
    import time

    d = Dragon(name="Timer", rarity=1, steps_count=2, is_active=True)
    db.add(d)
    db.flush()
    db.add(DragonStep(dragon_id=d.id, step_number=1, magic_action="A1"))
    u = User(vk_id=55, state="grow_step_2", current_dragon_id=d.id, current_step=2)
    db.add(u)
    soon = (datetime.now() + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S")
    ud = UserDragon(
        user_id=55, dragon_id=d.id,
        next_step_available_at=soon,
        timeout_notified=False,
    )
    db.add(ud)
    db.commit()

    vk_mock = MagicMock()
    _check_expired(db, vk_mock, logging.getLogger("test"))
    assert not vk_mock.messages.send.called

    time.sleep(1.5)

    _check_expired(db, vk_mock, logging.getLogger("test"))
    assert vk_mock.messages.send.called

    db.refresh(ud)
    assert ud.timeout_notified is True


def test_check_expired_skips_completed_dragon(db):
    from bot.scheduler import _check_expired

    d, u = _setup(db)
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == 1, UserDragon.dragon_id == d.id
    ).first()
    ud.completed_at = "2026-07-01T12:00:00"
    db.commit()

    vk_mock = MagicMock()
    _check_expired(db, vk_mock, logging.getLogger("test"))

    assert not vk_mock.messages.send.called
