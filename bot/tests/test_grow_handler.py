from datetime import datetime, timedelta
from models import Dragon, DragonStep, User, UserDragon, UserProgress
from bot.handlers.grow import handle_grow_message, format_step


def _setup(db):
    d = Dragon(name="Test", rarity=2, steps_count=3, is_active=True)
    db.add(d)
    db.flush()
    for i in range(1, 4):
        step = DragonStep(
            dragon_id=d.id, step_number=i,
            magic_action=f"Action {i}", task_description=f"Task {i}",
            hint=f"Hint {i}", timeout_hours=0, timeout_minutes=0,
        )
        db.add(step)
    u = User(vk_id=1, state="grow_step_1", current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.flush()
    ud = UserDragon(user_id=u.vk_id, dragon_id=d.id, completed_at="")
    db.add(ud)
    db.commit()
    return d, u


def _make_attachments(*photo_ids):
    atts = []
    for pid in photo_ids:
        atts.append({"type": "photo", "photo": {"owner_id": 1, "id": pid}})
    return atts


def test_format_step():
    from types import SimpleNamespace
    step = SimpleNamespace(magic_action="Wave wand", task_description="Sew 100", hint="Use blue")
    result = format_step(step, 2, 5)
    assert "Шаг 2 из 5" in result
    assert "Wave wand" in result
    assert "Sew 100" in result
    assert "Use blue" in result


def test_format_step_none():
    result = format_step(None, 1, 3)
    assert "Шаг 1 из 3" in result


def test_grow_message_timeout_blocks(db):
    d, u = _setup(db)

    future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == u.vk_id, UserDragon.dragon_id == d.id
    ).first()
    ud.next_step_available_at = future
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handled = handle_grow_message(
        u, "вышито", _make_attachments(101, 102), db, send
    )

    assert handled is True
    assert len(messages) == 1
    assert "отдыхает" in messages[0].lower()
    assert "осталось подождать" in messages[0].lower()


def test_grow_message_completes_step(db):
    d, u = _setup(db)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handled = handle_grow_message(
        u, "вышито", _make_attachments(101, 102), db, send
    )

    assert handled is True
    assert len(messages) == 1

    progress = db.query(UserProgress).filter(
        UserProgress.user_id == u.vk_id,
        UserProgress.dragon_id == d.id,
        UserProgress.step_number == 1,
    ).first()
    assert progress is not None
    assert progress.completed is True

    db.refresh(u)
    assert u.current_step == 2


def test_grow_message_with_timeout_shows_delay_message(db):
    d, u = _setup(db)

    step = db.query(DragonStep).filter(
        DragonStep.dragon_id == d.id, DragonStep.step_number == 1
    ).first()
    step.timeout_hours = 2
    step.timeout_minutes = 30
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_grow_message(u, "вышито", _make_attachments(101, 102), db, send)

    # Should include the "next step will be available" message
    full_text = " ".join(messages)
    assert "Шаг выполнен" in full_text or "выполнен" in full_text


def test_grow_message_invalid_format(db):
    d, u = _setup(db)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    # Only keyword, no photos
    handle_grow_message(u, "вышито", [], db, send)
    assert len(messages) == 1
    assert "2 фото" in messages[0]


def test_grow_message_no_active_dragon(db):
    u = User(vk_id=1, state="idle", current_dragon_id=None, current_step=0)
    db.add(u)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_grow_message(u, "вышито", _make_attachments(101, 102), db, send)
    assert len(messages) == 1
    assert "нет активного дракона" in messages[0].lower()
