from datetime import datetime, timedelta
from models import Dragon, DragonStep, User, UserDragon, UserProgress, Treasure, UserTreasure
from bot.services.grow_service import (
    get_dragon_step,
    get_total_steps,
    get_step_timeout,
    get_timeout_remaining,
    set_step_timeout,
    clear_step_timeout,
    complete_step,
    complete_dragon,
    award_treasure,
    rarity_name,
    rarity_stars,
)


def test_rarity_stars_clamped_at_three():
    assert rarity_stars(1) == "⭐"
    assert rarity_stars(2) == "⭐⭐"
    assert rarity_stars(3) == "⭐⭐⭐"
    assert rarity_stars(4) == "⭐⭐⭐"
    assert rarity_name(4) == "легендарный"


def _setup_dragon_with_step(db, step_number: int = 1, timeout_hours: int = 0, timeout_minutes: int = 0):
    d = Dragon(name="Test", rarity=1, steps_count=3, is_active=True)
    db.add(d)
    db.flush()
    step = DragonStep(
        dragon_id=d.id, step_number=step_number,
        timeout_hours=timeout_hours, timeout_minutes=timeout_minutes,
    )
    db.add(step)
    db.commit()
    return d, step


def _setup_user(db, vk_id: int = 1, dragon_id: int = 1):
    u = User(vk_id=vk_id, state="grow_step_1", current_dragon_id=dragon_id, current_step=1)
    db.add(u)
    db.commit()
    return u


def test_get_dragon_step(db):
    d, step = _setup_dragon_with_step(db)
    found = get_dragon_step(db, d.id, 1)
    assert found is not None
    assert found.id == step.id


def test_get_dragon_step_not_found(db):
    assert get_dragon_step(db, 999, 1) is None


def test_get_total_steps(db):
    d = Dragon(name="T", rarity=1, steps_count=5, is_active=True)
    db.add(d)
    db.commit()
    assert get_total_steps(db, d.id) == 5


def test_get_step_timeout_zero(db):
    d, _ = _setup_dragon_with_step(db, timeout_hours=0, timeout_minutes=0)
    h, m = get_step_timeout(db, d.id, 1)
    assert h == 0 and m == 0


def test_get_step_timeout_positive(db):
    d, _ = _setup_dragon_with_step(db, timeout_hours=2, timeout_minutes=30)
    h, m = get_step_timeout(db, d.id, 1)
    assert h == 2 and m == 30


def test_get_timeout_remaining_none_when_not_set(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    ud = UserDragon(user_id=1, dragon_id=d.id)
    db.add(ud)
    db.commit()
    assert get_timeout_remaining(db, 1, d.id) is None


def test_get_timeout_remaining_positive(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    future = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    ud = UserDragon(user_id=1, dragon_id=d.id, next_step_available_at=future)
    db.add(ud)
    db.commit()

    remaining = get_timeout_remaining(db, 1, d.id)
    assert remaining is not None
    assert remaining.total_seconds() > 3500  # ~2 hours


def test_get_timeout_remaining_short_expiry(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=7)
    db.add(u)
    db.flush()
    near_future = (datetime.now() + timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%S")
    ud = UserDragon(user_id=7, dragon_id=d.id, next_step_available_at=near_future)
    db.add(ud)
    db.commit()

    remaining = get_timeout_remaining(db, 7, d.id)
    assert remaining is not None
    assert 0.3 < remaining.total_seconds() < 5.0

    import time
    time.sleep(4.0)

    assert get_timeout_remaining(db, 7, d.id) is None


def test_get_timeout_remaining_expired(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    past = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")
    ud = UserDragon(user_id=1, dragon_id=d.id, next_step_available_at=past)
    db.add(ud)
    db.commit()

    assert get_timeout_remaining(db, 1, d.id) is None


def test_set_step_timeout(db):
    d, _ = _setup_dragon_with_step(db, timeout_hours=1, timeout_minutes=30)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    ud = UserDragon(user_id=1, dragon_id=d.id)
    db.add(ud)
    db.commit()

    set_step_timeout(db, 1, d.id, 1)
    db.refresh(ud)
    assert ud.next_step_available_at is not None
    assert ud.timeout_notified is False

    available = datetime.fromisoformat(ud.next_step_available_at)
    diff = available - datetime.now()
    assert diff.total_seconds() > 5000  # ~90 min


def test_set_step_timeout_zero_does_nothing(db):
    d, _ = _setup_dragon_with_step(db, timeout_hours=0, timeout_minutes=0)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    ud = UserDragon(user_id=1, dragon_id=d.id)
    db.add(ud)
    db.commit()

    set_step_timeout(db, 1, d.id, 1)
    db.refresh(ud)
    assert ud.next_step_available_at is None


def test_set_step_timeout_resets_notified_flag(db):
    d, _ = _setup_dragon_with_step(db, timeout_hours=1, timeout_minutes=0)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    ud = UserDragon(user_id=1, dragon_id=d.id, timeout_notified=True)
    db.add(ud)
    db.commit()

    set_step_timeout(db, 1, d.id, 1)
    db.refresh(ud)
    assert ud.timeout_notified is False


def test_clear_step_timeout(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    ud = UserDragon(
        user_id=1, dragon_id=d.id,
        next_step_available_at="2026-07-04T12:00:00",
    )
    db.add(ud)
    db.commit()

    clear_step_timeout(db, 1, d.id)
    db.refresh(ud)
    assert ud.next_step_available_at is None


def test_clear_step_timeout_noop_when_not_set(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    ud = UserDragon(user_id=1, dragon_id=d.id)
    db.add(ud)
    db.commit()

    clear_step_timeout(db, 1, d.id)
    db.refresh(ud)
    assert ud.next_step_available_at is None


def test_complete_step_creates_progress(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=1)
    db.add(u)
    db.commit()

    complete_step(db, 1, d.id, 1, photo_before_id="p1", photo_after_id="p2")

    progress = db.query(UserProgress).filter(
        UserProgress.user_id == 1,
        UserProgress.dragon_id == d.id,
        UserProgress.step_number == 1,
    ).first()
    assert progress is not None
    assert progress.completed is True
    assert progress.photo_before_id == "p1"
    assert progress.photo_after_id == "p2"


def test_complete_step_updates_existing(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    progress = UserProgress(
        user_id=1, dragon_id=d.id, step_number=1,
        completed=False, photo_before_id="", photo_after_id="",
    )
    db.add(progress)
    db.commit()

    complete_step(db, 1, d.id, 1, photo_before_id="new_before", photo_after_id="new_after")

    db.refresh(progress)
    assert progress.completed is True
    assert progress.photo_before_id == "new_before"
    assert progress.photo_after_id == "new_after"


def test_complete_dragon_sets_completed_at_and_clears_timeout(db):
    d, _ = _setup_dragon_with_step(db)
    u = User(vk_id=1)
    db.add(u)
    db.flush()
    ud = UserDragon(
        user_id=1, dragon_id=d.id,
        next_step_available_at="2026-07-04T12:00:00",
        timeout_notified=True,
    )
    db.add(ud)
    db.commit()

    complete_dragon(db, 1, d.id)
    db.refresh(ud)

    assert ud.completed_at != ""
    assert ud.next_step_available_at is None
    assert ud.timeout_notified is False


def _setup_rare_with_treasure(db, vk_id=1):
    d = Dragon(name="Rare", rarity=2, steps_count=1, is_active=True)
    db.add(d)
    db.flush()
    t = Treasure(name="Gem", description="Shiny", image_path="dragons/t.png", dragon_id=d.id, is_active=True)
    db.add(t)
    u = User(vk_id=vk_id)
    db.add(u)
    db.flush()
    db.add(UserDragon(user_id=vk_id, dragon_id=d.id, completed_at=""))
    db.commit()
    return d, t


def test_award_treasure_grants_once(db):
    d, t = _setup_rare_with_treasure(db)
    result = award_treasure(db, 1, d.id)
    assert result is not None
    assert result.id == t.id
    assert db.query(UserTreasure).filter(UserTreasure.user_id == 1).count() == 1


def test_award_treasure_idempotent(db):
    d, t = _setup_rare_with_treasure(db)
    first = award_treasure(db, 1, d.id)
    second = award_treasure(db, 1, d.id)
    assert first is not None
    assert second is None
    assert db.query(UserTreasure).filter(UserTreasure.user_id == 1).count() == 1


def test_award_treasure_none_when_no_treasure(db):
    d = Dragon(name="Rare2", rarity=2, steps_count=1, is_active=True)
    db.add(d)
    db.commit()
    result = award_treasure(db, 1, d.id)
    assert result is None
    assert db.query(UserTreasure).count() == 0


def test_award_treasure_none_for_non_rare(db):
    d = Dragon(name="Common", rarity=1, steps_count=1, is_active=True)
    db.add(d)
    db.flush()
    db.add(Treasure(name="Gem", dragon_id=d.id, is_active=True))
    db.commit()
    result = award_treasure(db, 1, d.id)
    assert result is None


def test_award_treasure_none_when_inactive(db):
    d = Dragon(name="Rare3", rarity=2, steps_count=1, is_active=True)
    db.add(d)
    db.flush()
    db.add(Treasure(name="Gem", dragon_id=d.id, is_active=False))
    db.commit()
    result = award_treasure(db, 1, d.id)
    assert result is None


def test_complete_dragon_returns_treasure(db):
    d, t = _setup_rare_with_treasure(db)
    result = complete_dragon(db, 1, d.id)
    assert result is not None
    assert result.id == t.id


def test_log_to_db_writes_errorlog(db):
    from bot.services.grow_service import log_to_db
    from models import ErrorLog

    log_to_db("bot", "UPLOAD", "upload failed", "traceback-here", 42, db)

    err = db.query(ErrorLog).filter(ErrorLog.user_id == 42).first()
    assert err is not None
    assert err.source == "bot"
    assert err.error_type == "UPLOAD"
    assert err.message == "upload failed"
    assert err.traceback_text == "traceback-here"


def test_notify_admin_logs_on_failure(db, monkeypatch):
    import config as _config
    from bot.services import grow_service
    from models import ErrorLog
    from .conftest import TestingSessionLocal

    monkeypatch.setattr(_config, "ADMIN_VK_ID", 12345)
    monkeypatch.setattr(_config, "VK_GROUP_TOKEN", "fake-token")
    monkeypatch.setattr("db.SessionLocal", TestingSessionLocal)

    def boom(*a, **kw):
        raise RuntimeError("VK down")

    monkeypatch.setattr("vk_api.VkApi", lambda *a, **kw: type("FakeVk", (), {"get_api": boom})())

    grow_service.notify_admin("test message")

    err = db.query(ErrorLog).filter(ErrorLog.error_type == "NOTIFY_ADMIN").first()
    assert err is not None
    assert err.source == "bot"
    assert "VK down" in err.message
    assert "test message" in err.message
