from datetime import datetime, timedelta, timezone
import config

MSK = timezone(timedelta(hours=3))


def _now_str():
    return datetime.now(MSK).strftime("%Y-%m-%dT%H:%M:%S")


def test_get_top_users_excludes_payments_test_vk_id(db, monkeypatch):
    monkeypatch.setattr(config, "PAYMENTS_TEST_VK_ID", 400977)
    from models import UserDragon, Dragon, User
    from bot.services.weekly_stats_service import _get_top_users

    now_str = _now_str()
    db.add(User(vk_id=400977, state="idle"))
    db.add(User(vk_id=500, state="idle"))
    for i in range(5):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()
    dragons = db.query(Dragon).all()
    for i in range(3):
        db.add(UserDragon(user_id=400977, dragon_id=dragons[i].id, completed_at=now_str))
    db.add(UserDragon(user_id=500, dragon_id=dragons[3].id, completed_at=now_str))
    db.commit()

    top = _get_top_users(db, 10)
    uids = [uid for uid, _ in top]
    assert 400977 not in uids
    assert 500 in uids


def test_get_top_users_respects_limit(db, monkeypatch):
    monkeypatch.setattr(config, "PAYMENTS_TEST_VK_ID", 400977)
    from models import UserDragon, Dragon, User
    from bot.services.weekly_stats_service import _get_top_users

    now_str = _now_str()
    for uid in (600, 601, 602):
        db.add(User(vk_id=uid, state="idle"))
    for i in range(3):
        db.add(Dragon(name=f"D{i}", rarity=1, steps_count=1, is_active=True))
    db.commit()
    dragons = db.query(Dragon).all()
    db.add(UserDragon(user_id=600, dragon_id=dragons[0].id, completed_at=now_str))
    db.add(UserDragon(user_id=601, dragon_id=dragons[1].id, completed_at=now_str))
    db.add(UserDragon(user_id=602, dragon_id=dragons[2].id, completed_at=now_str))
    db.commit()

    top = _get_top_users(db, 2)
    assert len(top) == 2
