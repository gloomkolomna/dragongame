from models import Dragon, DragonStep, User, UserDragon, UserInventory, ShopItem, SuspiciousReport
from bot.handlers.legend import handle_legend_start, handle_legend_mode, handle_legend_message, handle_legend_next


def _photos():
    return [
        {"type": "photo", "photo": {"owner_id": 1, "id": 10}},
        {"type": "photo", "photo": {"owner_id": 1, "id": 11}},
    ]


def _setup(db, fragments=2, rarity=3):
    d = Dragon(name="Leg", rarity=rarity, steps_count=1, is_active=True)
    db.add(d)
    db.flush()
    for i in range(1, fragments + 1):
        db.add(DragonStep(
            dragon_id=d.id, step_number=i, phase=1,
            task_description=f"Fragment {i}", crosses_norm=1000, image_path="",
        ))
    u = User(vk_id=1, state="idle", current_dragon_id=None, current_step=0, state_data="{}", stitches_balance=0)
    db.add(u)
    db.flush()
    db.add(UserDragon(user_id=1, dragon_id=d.id, completed_at="2026-01-01T00:00:00"))
    db.commit()
    return d, u


def test_legend_start_shows_fragment(db):
    d, u = _setup(db)
    msgs = []
    handle_legend_start(u, d.id, db, lambda m, **k: msgs.append(m))
    assert u.state == "legend_1"
    assert "отрывок 1 из 2" in msgs[0]


def test_legend_start_requires_completed(db):
    d, u = _setup(db)
    ud = db.query(UserDragon).filter(UserDragon.user_id == 1).first()
    ud.completed_at = ""
    db.commit()
    msgs = []
    handle_legend_start(u, d.id, db, lambda m, **k: msgs.append(m))
    assert "вырастить" in msgs[0].lower()


def test_legend_full_flow_gives_book(db):
    d, u = _setup(db, fragments=2)
    db.add(ShopItem(name="Книга обучения", is_legend_book=True, is_active=True))
    db.commit()

    def send(m, **k):
        pass

    handle_legend_start(u, d.id, db, send)
    handle_legend_mode(u, "norm", db, send)
    handle_legend_message(u, "вышито 1000", _photos(), db, send)
    assert u.state == "legend_1"

    handle_legend_next(u, db, send)
    assert u.state == "legend_2"

    handle_legend_mode(u, "norm", db, send)
    handle_legend_message(u, "вышито 1200", _photos(), db, send)

    db.refresh(u)
    assert u.state == "idle"
    assert u.stitches_balance == 2200
    inv = db.query(UserInventory).filter(UserInventory.user_id == 1).first()
    assert inv is not None


def test_legend_insufficient_crosses(db):
    d, u = _setup(db)
    msgs = []

    def send(m, **k):
        msgs.append(m)

    handle_legend_start(u, d.id, db, send)
    handle_legend_mode(u, "norm", db, send)
    handle_legend_message(u, "вышито 100", _photos(), db, send)
    assert any("не менее" in m.lower() for m in msgs)


def test_legend_anti_cheat(db):
    d, u = _setup(db)

    def send(m, **k):
        pass

    handle_legend_start(u, d.id, db, send)
    handle_legend_mode(u, "x2", db, send)
    handle_legend_message(u, "вышито 8000", _photos(), db, send)
    report = db.query(SuspiciousReport).filter(SuspiciousReport.user_id == 1).first()
    assert report is not None
    assert report.mode == "x2"
    assert report.normal_crosses == 2000
