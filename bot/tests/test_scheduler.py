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


def test_check_care_due_uses_epic_name(db):
    from bot.scheduler import _check_care_due
    from models import EpicCareState, EpicStage
    from services import epic_service

    ed = Dragon(name="EpicSched", rarity=3, steps_count=1, is_active=True, is_epic=True, egg_type="лунное")
    db.add(ed)
    db.flush()
    u = User(vk_id=900, state="idle", epic_unlocked=True, epic_dragon_id=ed.id)
    db.add(u)
    ud = UserDragon(user_id=900, dragon_id=ed.id, completed_at="")
    db.add(ud)
    st = EpicStage(dragon_id=ed.id, stage_number=1, name="S1", cycles_count=1)
    db.add(st)
    db.flush()
    past = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
    db.add(EpicCareState(user_dragon_id=ud.id, stage_id=st.id, next_action_at=past, care_notified=False))
    db.commit()
    epic_service.set_epic_name(db, 900, "Пепел")

    vk_mock = MagicMock()
    _check_care_due(db, vk_mock, logging.getLogger("test"))

    assert vk_mock.messages.send.called
    msg = vk_mock.messages.send.call_args[1].get("message", "")
    assert "Пепел" in msg


def test_check_care_due_injects_legendary_button(db):
    import json
    from bot.scheduler import _check_care_due
    from models import EpicCareState, EpicStage, DragonStep, UserLegendProgress
    from services import epic_service

    ed = Dragon(name="EpicSched2", rarity=3, steps_count=1, is_active=True, is_epic=True, egg_type="лунное")
    db.add(ed)
    db.flush()
    leg = Dragon(name="Легенда", rarity=3, steps_count=1, is_active=True, is_epic=False)
    db.add(leg)
    db.flush()
    db.add(DragonStep(dragon_id=leg.id, step_number=1, phase=1))
    u = User(vk_id=901, state="idle", epic_unlocked=True, epic_dragon_id=ed.id)
    db.add(u)
    ud = UserDragon(user_id=901, dragon_id=ed.id, completed_at="")
    db.add(ud)
    db.add(UserDragon(user_id=901, dragon_id=leg.id, completed_at="2026-07-01T12:00:00"))
    st = EpicStage(dragon_id=ed.id, stage_number=1, name="S1", cycles_count=1)
    db.add(st)
    db.flush()
    past = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
    db.add(EpicCareState(user_dragon_id=ud.id, stage_id=st.id, next_action_at=past, care_notified=False))
    db.commit()

    vk_mock = MagicMock()
    _check_care_due(db, vk_mock, logging.getLogger("test"))

    assert vk_mock.messages.send.called
    kb = vk_mock.messages.send.call_args[1].get("keyboard", "")
    payloads = [
        b.get("action", {}).get("payload", "")
        for row in json.loads(kb)["buttons"] for b in row
    ]
    cmds = [json.loads(p).get("cmd") for p in payloads if p]
    assert "legends" in cmds
    assert "garden" in cmds
