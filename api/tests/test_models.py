from models import Dragon, DragonStep, User, UserDragon, UserProgress


def test_create_dragon(db):
    d = Dragon(name="Test", rarity=3, steps_count=3, is_active=True)
    db.add(d)
    db.commit()
    assert d.id is not None
    assert d.name == "Test"


def test_create_dragon_step_with_timeout(db):
    d = Dragon(name="Test", rarity=2, steps_count=2, is_active=True)
    db.add(d)
    db.flush()

    step = DragonStep(
        dragon_id=d.id, step_number=1,
        timeout_hours=5, timeout_minutes=30,
    )
    db.add(step)
    db.commit()

    assert step.timeout_hours == 5
    assert step.timeout_minutes == 30


def test_dragon_step_defaults(db):
    d = Dragon(name="Test", rarity=1, steps_count=1, is_active=True)
    db.add(d)
    db.flush()

    step = DragonStep(dragon_id=d.id, step_number=1)
    db.add(step)
    db.commit()

    assert step.timeout_hours == 0
    assert step.timeout_minutes == 0


def test_user_dragon_timeout_fields(db):
    user = User(vk_id=123)
    dragon = Dragon(name="D", rarity=1, steps_count=1, is_active=True)
    db.add(user)
    db.add(dragon)
    db.flush()

    ud = UserDragon(user_id=user.vk_id, dragon_id=dragon.id)
    db.add(ud)
    db.commit()

    assert ud.next_step_available_at is None
    assert ud.timeout_notified is False

    ud.next_step_available_at = "2026-07-04T12:00:00"
    ud.timeout_notified = True
    db.commit()

    assert ud.next_step_available_at == "2026-07-04T12:00:00"
    assert ud.timeout_notified is True
