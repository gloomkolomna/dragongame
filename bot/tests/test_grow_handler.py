from datetime import datetime, timedelta
from models import Dragon, DragonStep, User, UserDragon, UserProgress
from bot.handlers.grow import handle_grow_message, format_step


def _setup(db, state="grow_step_1_norm"):
    d = Dragon(name="Test", rarity=2, steps_count=3, is_active=True)
    db.add(d)
    db.flush()
    for i in range(1, 4):
        step = DragonStep(
            dragon_id=d.id, step_number=i,
            magic_action=f"Action {i}", task_description=f"Task {i}",
            hint=f"Hint {i}", timeout_hours=0, timeout_minutes=0,
            crosses_norm=1000,
        )
        db.add(step)
    u = User(vk_id=1, state=state, current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.flush()
    ud = UserDragon(user_id=u.vk_id, dragon_id=d.id, completed_at="")
    db.add(ud)
    db.commit()
    return d, u


def _photos():
    return [
        {"type": "photo", "photo": {"owner_id": 1, "id": 10}},
        {"type": "photo", "photo": {"owner_id": 1, "id": 11}},
        {"type": "photo", "photo": {"owner_id": 1, "id": 12}},
    ]


def test_format_step():
    from types import SimpleNamespace
    step = SimpleNamespace(magic_action="Wave wand", task_description="Sew 100", hint="Use blue", crosses_norm=500)
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

    handled = handle_grow_message(u, "вышито 1000", [], db, send)

    assert handled is True
    assert len(messages) == 1
    assert "подождать" in messages[0].lower()


def test_grow_message_completes_step(db):
    d, u = _setup(db)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handled = handle_grow_message(u, "вышито 1500", _photos(), db, send)

    assert handled is True
    assert len(messages) >= 1

    progress = db.query(UserProgress).filter(
        UserProgress.user_id == u.vk_id,
        UserProgress.dragon_id == d.id,
        UserProgress.step_number == 1,
    ).first()
    assert progress is not None
    assert progress.completed is True
    assert progress.photo_before_id == "photo1_10"
    assert progress.photo_after_id == "photo1_11"

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

    handle_grow_message(u, "вышито 1500", _photos(), db, send)

    full_text = " ".join(messages)
    assert "выполнен" in full_text


def test_grow_message_insufficient_crosses(db):
    d, u = _setup(db)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_grow_message(u, "вышито 100", [], db, send)

    assert len(messages) == 1
    assert "не менее" in messages[0].lower()
    assert "1000" in messages[0]

    progress = db.query(UserProgress).filter(
        UserProgress.user_id == u.vk_id,
        UserProgress.dragon_id == d.id,
        UserProgress.step_number == 1,
    ).first()
    assert progress is None or progress.completed == False


def test_grow_message_insufficient_photos(db):
    d, u = _setup(db)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handled = handle_grow_message(u, "вышито 1500", [], db, send)

    assert handled is True
    assert len(messages) == 1
    assert "фото" in messages[0]


def test_grow_message_no_active_dragon(db):
    u = User(vk_id=1, state="idle", current_dragon_id=None, current_step=0)
    db.add(u)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_grow_message(u, "вышито 1000", [], db, send)
    assert len(messages) == 1
    assert "нет активного яйца дракона" in messages[0].lower()


def test_grow_message_complete_dragon_rarity_word(db):
    d = Dragon(name="Final", rarity=1, steps_count=1, is_active=True)
    db.add(d)
    db.flush()
    db.add(DragonStep(
        dragon_id=d.id, step_number=1, magic_action="A", task_description="T",
        timeout_hours=0, timeout_minutes=0, crosses_norm=1000,
    ))
    u = User(vk_id=5, state="grow_step_1_norm", current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.flush()
    db.add(UserDragon(user_id=u.vk_id, dragon_id=d.id, completed_at=""))
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_grow_message(u, "вышито 1500", _photos(), db, send)

    full = " ".join(messages)
    assert "обычный" in full
    assert "обычный ⭐" in full


def test_grow_message_credits_actual_crosses(db):
    d, u = _setup(db)

    def send(msg, **kw):
        pass

    handle_grow_message(u, "вышито 1500", _photos(), db, send)

    db.refresh(u)
    assert u.stitches_balance == 1500


def test_grow_message_credits_accumulate(db):
    d, u = _setup(db)
    u.stitches_balance = 500
    db.commit()

    def send(msg, **kw):
        pass

    handle_grow_message(u, "вышито 1200", _photos(), db, send)

    db.refresh(u)
    assert u.stitches_balance == 1700


def test_grow_message_no_credit_when_insufficient(db):
    d, u = _setup(db)

    def send(msg, **kw):
        pass

    handle_grow_message(u, "вышито 100", _photos(), db, send)

    db.refresh(u)
    assert u.stitches_balance == 0


def test_grow_message_anti_cheat_creates_report(db):
    from models import SuspiciousReport
    d, u = _setup(db)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_grow_message(u, "вышито 4000", _photos(), db, send)

    db.refresh(u)
    assert u.stitches_balance == 4000

    report = db.query(SuspiciousReport).filter(SuspiciousReport.user_id == u.vk_id).first()
    assert report is not None
    assert report.status == "pending"
    assert report.declared_crosses == 4000
    assert report.normal_crosses == 1000
    assert report.mode == "norm"
    assert report.photo_before_id == "photo1_10"
    assert report.raw_message == "вышито 4000"
    assert any("подозрительным" in m.lower() for m in messages)


def test_grow_message_anti_cheat_x2_threshold(db):
    from models import SuspiciousReport
    d, u = _setup(db, state="grow_step_1_x2")

    def send(msg, **kw):
        pass

    handle_grow_message(u, "вышито 8000", _photos(), db, send)
    report = db.query(SuspiciousReport).filter(SuspiciousReport.user_id == u.vk_id).first()
    assert report is not None
    assert report.mode == "x2"
    assert report.normal_crosses == 2000
    assert report.declared_crosses == 8000


def test_grow_message_x2_not_suspicious_below_threshold(db):
    from models import SuspiciousReport
    d, u = _setup(db, state="grow_step_1_x2")

    def send(msg, **kw):
        pass

    handle_grow_message(u, "вышито 5000", _photos(), db, send)
    report = db.query(SuspiciousReport).filter(SuspiciousReport.user_id == u.vk_id).first()
    assert report is None
    db.refresh(u)
    assert u.stitches_balance == 5000


def test_grow_message_blocked_over_5x(db):
    from models import SuspiciousReport
    d, u = _setup(db)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_grow_message(u, "вышито 6000", _photos(), db, send)

    db.refresh(u)
    assert u.stitches_balance == 0
    assert u.current_step == 1
    assert any("слишком много" in m for m in messages)

    report = db.query(SuspiciousReport).filter(SuspiciousReport.user_id == u.vk_id).first()
    assert report is not None
    assert report.declared_crosses == 6000


def test_grow_message_blocked_over_5x_x2(db):
    from models import SuspiciousReport
    d, u = _setup(db, state="grow_step_1_x2")

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_grow_message(u, "вышито 11000", _photos(), db, send)

    db.refresh(u)
    assert u.stitches_balance == 0
    assert u.current_step == 1
    assert any("слишком много" in m for m in messages)

    report = db.query(SuspiciousReport).filter(SuspiciousReport.user_id == u.vk_id).first()
    assert report is not None
    assert report.mode == "x2"
    assert report.normal_crosses == 2000
    assert report.declared_crosses == 11000


def test_grow_message_no_report_within_threshold(db):
    from models import SuspiciousReport
    d, u = _setup(db)

    def send(msg, **kw):
        pass

    handle_grow_message(u, "вышито 2500", _photos(), db, send)

    report = db.query(SuspiciousReport).filter(SuspiciousReport.user_id == u.vk_id).first()
    assert report is None


def _setup_final_rare(db, with_treasure=True):
    from models import Treasure
    d = Dragon(name="RareFinal", rarity=2, steps_count=1, is_active=True)
    db.add(d)
    db.flush()
    db.add(DragonStep(
        dragon_id=d.id, step_number=1, magic_action="A", task_description="T",
        timeout_hours=0, timeout_minutes=0, crosses_norm=1000,
    ))
    if with_treasure:
        db.add(Treasure(name="Кристалл", description="Сияющий", image_path="dragons/tr.png", dragon_id=d.id, is_active=True))
    u = User(vk_id=7, state="grow_step_1_norm", current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.flush()
    db.add(UserDragon(user_id=u.vk_id, dragon_id=d.id, completed_at=""))
    db.commit()
    return d, u


def test_grow_message_rare_final_sends_treasure_with_photo(db, monkeypatch):
    d, u = _setup_final_rare(db)
    monkeypatch.setattr("bot.handlers.grow.os.path.isfile", lambda p: True)

    sent = []
    def send(msg, **kw):
        sent.append((msg, kw))

    uploads = []
    def upload_image(filepath, **kw):
        uploads.append(filepath)
        return "photo1_1"

    handle_grow_message(u, "вышито 1500", _photos(), db, send, upload_image)

    treasure_msgs = [(m, kw) for m, kw in sent if "пещере появилось новое сокровище" in m]
    assert len(treasure_msgs) == 1
    msg, kw = treasure_msgs[0]
    assert "Кристалл" in msg
    assert "Сияющий" in msg
    assert kw.get("attachment") == "photo1_1"
    assert any("tr.png" in p for p in uploads)


def test_grow_message_rare_final_no_treasure_only_savings(db):
    d, u = _setup_final_rare(db, with_treasure=False)

    sent = []
    def send(msg, **kw):
        sent.append(msg)

    handle_grow_message(u, "вышито 1500", _photos(), db, send)

    assert not any("пещере появилось новое сокровище" in m for m in sent)
    db.refresh(u)
    assert u.stitches_balance == 1500


def test_grow_message_legendary_final_mentions_library(db):
    d = Dragon(name="Legend", rarity=3, steps_count=1, is_active=True, legend_image_path="dragons/cov.png")
    db.add(d)
    db.flush()
    db.add(DragonStep(
        dragon_id=d.id, step_number=1, magic_action="A", task_description="T",
        timeout_hours=0, timeout_minutes=0, crosses_norm=1000,
    ))
    db.add(DragonStep(dragon_id=d.id, step_number=1, phase=1, magic_action="L", task_description="LT"))
    u = User(vk_id=8, state="grow_step_1_norm", current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.flush()
    db.add(UserDragon(user_id=u.vk_id, dragon_id=d.id, completed_at=""))
    db.commit()

    sent = []
    def send(msg, **kw):
        sent.append(msg)

    handle_grow_message(u, "вышито 1500", _photos(), db, send)

    assert any("Библиотек" in m for m in sent)


def test_step_attachment_prefers_step_image(monkeypatch):
    from types import SimpleNamespace
    from bot.handlers import grow

    monkeypatch.setattr(grow.os.path, "isfile", lambda p: True)
    captured = {}

    def fake_upload(filepath, **kw):
        captured["filepath"] = filepath
        return "photoX"

    user = SimpleNamespace(vk_id=1)
    dragon = SimpleNamespace(egg_path="dragons/egg.png")
    step = SimpleNamespace(image_path="dragons/step5.png")

    result = grow.step_attachment(None, user, dragon, step, fake_upload)
    assert result == "photoX"
    assert captured["filepath"].endswith("step5.png")


def test_step_attachment_falls_back_to_egg(monkeypatch):
    from types import SimpleNamespace
    from bot.handlers import grow

    monkeypatch.setattr(grow.os.path, "isfile", lambda p: True)
    captured = {}

    def fake_upload(filepath, **kw):
        captured["filepath"] = filepath
        return "photoEgg"

    user = SimpleNamespace(vk_id=1)
    dragon = SimpleNamespace(egg_path="dragons/egg.png")
    step = SimpleNamespace(image_path="")

    result = grow.step_attachment(None, user, dragon, step, fake_upload)
    assert result == "photoEgg"
    assert captured["filepath"].endswith("egg.png")
