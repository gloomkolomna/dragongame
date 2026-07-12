from datetime import datetime, timedelta
from models import Dragon, DragonStep, User, UserDragon, UserProgress
from bot.handlers.commands import (
    handle_start, handle_switch_to,
    handle_garden, cancel_garden, switch_dragon,
    handle_balance, handle_legends, handle_legends_pick, cancel_legends,
    grown_legendaries, user_has_legendary,
)
from bot.fsm import IDLE, AWAIT_GARDEN, AWAIT_LEGENDS


def _setup_user_with_dragon(db, step=1, timeout_hours=0, timeout_minutes=0):
    d = Dragon(name="Ice", rarity=3, steps_count=5, is_active=True)
    db.add(d)
    db.flush()
    for i in range(1, 6):
        db.add(DragonStep(
            dragon_id=d.id, step_number=i,
            magic_action=f"Action {i}", task_description=f"Task {i}",
            timeout_hours=timeout_hours, timeout_minutes=timeout_minutes,
        ))
    u = User(
        vk_id=42, state=f"grow_step_{step}",
        current_dragon_id=d.id, current_step=step,
    )
    db.add(u)
    db.flush()
    ud = UserDragon(user_id=u.vk_id, dragon_id=d.id, completed_at="")
    db.add(ud)
    db.commit()
    return d, u


def test_handle_start_shows_timeout(db):
    d, u = _setup_user_with_dragon(db, step=1)
    future = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == u.vk_id, UserDragon.dragon_id == d.id
    ).first()
    ud.next_step_available_at = future
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_start(u, db, send)

    full = " ".join(messages)
    assert "⏳" in full or "Готов" in full


def test_handle_balance_shows_balance(db):
    u = User(vk_id=77, state=IDLE, stitches_balance=2500)
    db.add(u)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_balance(u, db, send)

    assert len(messages) == 1
    assert "2500" in messages[0]
    assert "опилк" in messages[0]


def test_handle_balance_zero(db):
    u = User(vk_id=78, state=IDLE)
    db.add(u)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_balance(u, db, send)
    assert "0" in messages[0]


def test_handle_switch_to_switches_dragon(db):
    d1 = Dragon(name="Alpha", rarity=2, steps_count=3, is_active=True)
    d2 = Dragon(name="Beta", rarity=2, steps_count=3, is_active=True)
    db.add_all([d1, d2])
    db.flush()
    for i in range(1, 4):
        db.add_all([
            DragonStep(dragon_id=d1.id, step_number=i, magic_action=f"A{i}"),
            DragonStep(dragon_id=d2.id, step_number=i, magic_action=f"B{i}"),
        ])
    u = User(vk_id=10, state="grow_step_2", current_dragon_id=d1.id, current_step=2)
    db.add(u)
    ud2 = UserDragon(user_id=10, dragon_id=d2.id, completed_at="")
    db.add(ud2)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_switch_to(u, d2.id, db, send)

    db.refresh(u)
    assert u.current_dragon_id == d2.id
    assert u.current_step == 1
    assert u.state == "grow_step_1"

    full = " ".join(messages)
    assert "Beta" in full or "Переключился" in full


def test_handle_switch_to_completed_dragon(db):
    d = Dragon(name="Done", rarity=1, steps_count=2, is_active=True)
    db.add(d)
    db.flush()
    u = User(vk_id=10, state=IDLE, current_dragon_id=None, current_step=0)
    db.add(u)
    ud = UserDragon(user_id=10, dragon_id=d.id, completed_at="2026-07-01T12:00:00")
    db.add(ud)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_switch_to(u, d.id, db, send)

    assert len(messages) == 1
    assert "выращен" in messages[0]


def test_handle_garden_lists_dragons(db):
    d = Dragon(name="GardenDragon", rarity=3, steps_count=3, is_active=True)
    db.add(d)
    db.flush()
    u = User(vk_id=20, state="grow_step_1", current_dragon_id=d.id, current_step=1)
    db.add(u)
    ud = UserDragon(user_id=20, dragon_id=d.id, completed_at="")
    db.add(ud)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_garden(u, db, send)

    full = " ".join(messages)
    assert "GardenDragon" in full
    assert u.state == AWAIT_GARDEN


def test_handle_garden_excludes_completed_keeps_numbers(db):
    d1 = Dragon(name="Grown1", rarity=1, steps_count=2, is_active=True, egg_type="золотое")
    d2 = Dragon(name="Grown2", rarity=1, steps_count=2, is_active=True, egg_type="серебряное")
    d3 = Dragon(name="Growing", rarity=1, steps_count=2, is_active=True, egg_type="красное")
    db.add_all([d1, d2, d3])
    db.flush()
    u = User(vk_id=22, state="grow_step_1", current_dragon_id=d3.id, current_step=1)
    db.add(u)
    db.add_all([
        UserDragon(user_id=22, dragon_id=d1.id, completed_at="2026-07-01T12:00:00"),
        UserDragon(user_id=22, dragon_id=d2.id, completed_at="2026-07-02T12:00:00"),
        UserDragon(user_id=22, dragon_id=d3.id, completed_at=""),
    ])
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_garden(u, db, send)

    full = " ".join(messages)
    assert "Grown1" not in full
    assert "Grown2" not in full
    assert "золотое" not in full
    assert "серебряное" not in full
    assert "3. 🥚 красное" in full
    assert "Выращено драконов: 2" in full
    assert "Мой Бестиарий" in full
    assert "Напиши номер яйца" in full


def test_handle_garden_shows_incubation_time(db):
    d = Dragon(name="TimerEgg", rarity=2, steps_count=3, is_active=True, egg_type="ледяное")
    db.add(d)
    db.flush()
    u = User(vk_id=21, state="grow_step_2", current_dragon_id=d.id, current_step=2)
    db.add(u)
    db.flush()
    future = (datetime.now() + timedelta(hours=3, minutes=15)).strftime("%Y-%m-%dT%H:%M:%S")
    ud = UserDragon(user_id=21, dragon_id=d.id, completed_at="", next_step_available_at=future)
    db.add(ud)
    db.add(UserProgress(user_id=21, dragon_id=d.id, step_number=1, completed=True))
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_garden(u, db, send)

    full = " ".join(messages)
    assert "🟡" in full
    assert "ещё 3 ч." in full


def test_cancel_garden_restores_state(db):
    d, u = _setup_user_with_dragon(db, step=2)
    u.state = AWAIT_GARDEN
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    cancel_garden(u, db, send)

    assert u.state == "grow_step_2"
    assert "Остаёмся" in " ".join(messages)


def test_switch_dragon_by_index(db):
    d1 = Dragon(name="First", rarity=1, steps_count=2, is_active=True)
    d2 = Dragon(name="Second", rarity=1, steps_count=2, is_active=True)
    db.add_all([d1, d2])
    db.flush()
    u = User(vk_id=30, state="grow_step_1", current_dragon_id=d1.id, current_step=1)
    db.add(u)
    for i in range(1, 3):
        db.add(DragonStep(dragon_id=d1.id, step_number=i, magic_action=f"A{i}"))
        db.add(DragonStep(dragon_id=d2.id, step_number=i, magic_action=f"B{i}"))
    ud1 = UserDragon(user_id=30, dragon_id=d1.id, completed_at="")
    ud2 = UserDragon(user_id=30, dragon_id=d2.id, completed_at="")
    db.add_all([ud1, ud2])
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    switch_dragon(u, 2, db, send)

    db.refresh(u)
    assert u.current_dragon_id == d2.id


def test_switch_dragon_timeout_attaches_egg(db):
    import os
    from bot.handlers import commands as cmd
    d1 = Dragon(name="First", rarity=1, steps_count=2, is_active=True)
    egg_file = os.path.join(cmd._IMAGES, "egg_switch_test.png")
    d2 = Dragon(name="Second", rarity=1, steps_count=2, is_active=True,
                egg_type="ледяное", egg_path=os.path.basename(egg_file))
    db.add_all([d1, d2])
    db.flush()
    u = User(vk_id=31, state="grow_step_1", current_dragon_id=d1.id, current_step=1)
    db.add(u)
    for i in range(1, 3):
        db.add(DragonStep(dragon_id=d1.id, step_number=i, magic_action=f"A{i}"))
        db.add(DragonStep(dragon_id=d2.id, step_number=i, magic_action=f"B{i}"))
    ud1 = UserDragon(user_id=31, dragon_id=d1.id, completed_at="")
    future = (datetime.now() + timedelta(hours=47, minutes=39)).strftime("%Y-%m-%dT%H:%M:%S")
    ud2 = UserDragon(user_id=31, dragon_id=d2.id, completed_at="", next_step_available_at=future)
    db.add_all([ud1, ud2])
    db.commit()

    os.makedirs(cmd._IMAGES, exist_ok=True)
    with open(egg_file, "wb") as f:
        f.write(b"\x89PNG")

    attachments = []
    def send(msg, **kw):
        attachments.append(kw.get("attachment"))

    uploaded = []
    def upload_image(path, **kw):
        uploaded.append(path)
        return "photo123"

    try:
        switch_dragon(u, 2, db, send, upload_image)
    finally:
        os.remove(egg_file)

    assert uploaded and uploaded[0] == egg_file
    assert "photo123" in attachments


def _make_epic(db, vk_id, steps_count=2, hatched_steps=0, name=""):
    ed = Dragon(name="EpicOne", rarity=3, steps_count=steps_count, is_active=True, is_epic=True, egg_type="лунное")
    db.add(ed)
    db.flush()
    for i in range(1, steps_count + 1):
        db.add(DragonStep(dragon_id=ed.id, step_number=i, magic_action=f"E{i}", crosses_norm=1000))
    for i in range(1, hatched_steps + 1):
        db.add(UserProgress(user_id=vk_id, dragon_id=ed.id, step_number=i, completed=True))
    u = db.query(User).filter(User.vk_id == vk_id).first()
    u.epic_dragon_id = ed.id
    if name:
        db.add(UserProgress(user_id=vk_id, dragon_id=ed.id, step_number=0, completed=False, epic_name=name))
    db.commit()
    return ed


def test_handle_garden_includes_epic_with_emoji(db):
    d = Dragon(name="Reg", rarity=1, steps_count=2, is_active=True, egg_type="красное")
    db.add(d)
    db.flush()
    u = User(vk_id=50, state="grow_step_1", current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.add(UserDragon(user_id=50, dragon_id=d.id, completed_at=""))
    db.commit()
    _make_epic(db, 50)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_garden(u, db, send)

    full = " ".join(messages)
    assert "🐲" in full
    assert "2. " in full
    assert u.state == AWAIT_GARDEN


def test_switch_to_epic_number_routes_to_epic(db):
    d = Dragon(name="Reg", rarity=1, steps_count=2, is_active=True, egg_type="красное")
    db.add(d)
    db.flush()
    u = User(vk_id=51, state=AWAIT_GARDEN, current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.add(UserDragon(user_id=51, dragon_id=d.id, completed_at=""))
    db.commit()
    _make_epic(db, 51)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    switch_dragon(u, 2, db, send)

    db.refresh(u)
    assert u.state.startswith("epic_egg_")


def test_handle_garden_excludes_hatched_epic(db):
    d = Dragon(name="Reg", rarity=1, steps_count=2, is_active=True, egg_type="красное")
    db.add(d)
    db.flush()
    u = User(vk_id=52, state="grow_step_1", current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.add(UserDragon(user_id=52, dragon_id=d.id, completed_at=""))
    db.commit()
    _make_epic(db, 52, steps_count=2, hatched_steps=2, name="Уголёк")

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_garden(u, db, send)

    full = " ".join(messages)
    assert "Уголёк" not in full
    assert "2. " not in full


def _make_legendary(db, vk_id, name="Legendary", fragments=2, opened=0):
    from models import UserLegendProgress
    d = Dragon(name=name, rarity=3, steps_count=1, is_active=True, legend_title=f"{name} legend")
    db.add(d)
    db.flush()
    for i in range(1, fragments + 1):
        db.add(DragonStep(dragon_id=d.id, step_number=i, phase=1, task_description=f"F{i}", crosses_norm=100))
    db.add(UserDragon(user_id=vk_id, dragon_id=d.id, completed_at="2026-07-01T00:00:00"))
    for i in range(1, opened + 1):
        db.add(UserLegendProgress(user_id=vk_id, dragon_id=d.id, fragment_number=i, completed=True))
    db.commit()
    return d


def test_user_has_legendary(db):
    u = User(vk_id=60, state=IDLE)
    db.add(u)
    db.commit()
    assert user_has_legendary(db, 60) is False
    _make_legendary(db, 60)
    assert user_has_legendary(db, 60) is True


def test_grown_legendary_requires_completed(db):
    from models import Dragon as D
    u = User(vk_id=61, state=IDLE)
    db.add(u)
    d = D(name="NotGrown", rarity=3, steps_count=1, is_active=True)
    db.add(d)
    db.flush()
    db.add(DragonStep(dragon_id=d.id, step_number=1, phase=1))
    db.add(UserDragon(user_id=61, dragon_id=d.id, completed_at=""))
    db.commit()
    assert grown_legendaries(db, 61) == []


def test_handle_legends_lists_and_pick_starts(db):
    u = User(vk_id=62, state=IDLE)
    db.add(u)
    db.commit()
    d = _make_legendary(db, 62, name="Dracus", fragments=2, opened=0)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_legends(u, db, send)
    assert u.state == AWAIT_LEGENDS
    assert "Dracus" in " ".join(messages)

    messages.clear()
    handle_legends_pick(u, 1, db, send)
    assert u.state.startswith("legend_")
    assert any("Dracus" in m for m in messages)


def test_handle_legends_empty(db):
    u = User(vk_id=63, state=IDLE)
    db.add(u)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_legends(u, db, send)
    assert u.state == IDLE
    assert "нет выращенных легендарных" in " ".join(messages)


def test_cancel_legends_restores_state(db):
    u = User(vk_id=64, state=AWAIT_LEGENDS, current_dragon_id=99, current_step=3)
    db.add(u)
    db.commit()

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    cancel_legends(u, db, send)
    assert u.state == "grow_step_3"


def test_cancel_garden_restores_epic_state(db):
    d = Dragon(name="Reg", rarity=1, steps_count=2, is_active=True, egg_type="красное")
    db.add(d)
    db.flush()
    u = User(vk_id=70, state="epic_egg_2", current_dragon_id=d.id, current_step=1)
    db.add(u)
    db.add(UserDragon(user_id=70, dragon_id=d.id, completed_at=""))
    db.commit()
    _make_epic(db, 70)

    messages = []
    def send(msg, **kw):
        messages.append(msg)

    handle_garden(u, db, send)
    assert u.state == AWAIT_GARDEN

    cancel_garden(u, db, send)
    assert u.state == "epic_egg_2", f"Expected epic_egg_2, got {u.state}"
