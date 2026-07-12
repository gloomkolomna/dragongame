from models import User, Dragon, DragonStep, UserDragon, UserProgress, ShopItem, UserInventory
from models import EpicStage, EpicStageAction, EpicActionItem, EpicCareState, EpicMoodlet
from bot.handlers.epic import handle_epic_name, send_epic_spawn_notice
from bot.handlers.epic_care import handle_epic_restart, show_care_action, handle_care_mode, handle_care_message
from services import epic_service


def _epic(db, vk=10, steps=1):
    d = Dragon(name="Epi", rarity=1, steps_count=steps, is_active=True, is_epic=True, egg_type="Тень")
    db.add(d)
    db.flush()
    for i in range(1, steps + 1):
        db.add(DragonStep(dragon_id=d.id, step_number=i, phase=0, crosses_norm=1000))
    u = User(vk_id=vk, state="idle", stitches_balance=500)
    db.add(u)
    db.flush()
    db.add(UserDragon(user_id=vk, dragon_id=d.id, completed_at=""))
    db.commit()
    return u, d


def _photos():
    return [{"type": "photo", "photo": {"owner_id": 1, "id": 10}}]


def test_epic_name_sets_and_triggers_care(db):
    u, d = _epic(db)
    u.state = "await_epic_name"
    u.epic_unlocked = True
    u.epic_dragon_id = d.id
    db.commit()
    st = EpicStage(stage_number=1, name="S1", cycles_count=1)
    db.add(st)
    db.flush()
    a = EpicStageAction(stage_id=st.id, dragon_id=d.id, action_label="кормить", order_in_cycle=0, crosses_norm=1000)
    db.add(a)
    db.commit()
    msgs = []

    def send(m, **k):
        msgs.append(m)

    handle_epic_name(u, "Уголёк", db, send)
    db.refresh(u)
    assert u.state.startswith("epic_care_")
    assert any("Уголёк" in m for m in msgs)


def test_epic_name_no_stages_goes_idle(db):
    u, d = _epic(db, vk=11)
    u.state = "await_epic_name"
    u.epic_unlocked = True
    u.epic_dragon_id = d.id
    db.commit()
    msgs = []
    handle_epic_name(u, "БезСтадий", db, lambda m, **k: msgs.append(m))
    db.refresh(u)
    assert u.state == "idle"


def test_epic_restart_same_clears_slot(db):
    u, d = _epic(db, vk=12)
    u.epic_unlocked = True
    u.epic_dragon_id = d.id
    ud = db.query(UserDragon).filter(UserDragon.user_id == 12).first()
    ud.completed_at = "2026-01-01"
    db.commit()
    msgs = []
    handle_epic_restart(u, "same", db, lambda m, **k: msgs.append(m))
    db.refresh(u)
    assert u.state == "epic_egg_1"
    ud2 = db.query(UserDragon).filter(UserDragon.user_id == 12).first()
    assert ud2.completed_at == ""


def test_epic_spawn_notice_has_garden_button(db):
    u, d = _epic(db, vk=15)
    d.egg_path = ""
    sent = {}
    send = lambda m, **k: sent.update(k)
    send_epic_spawn_notice(d, u, db, send)
    assert "🔄🥚 Сменить яйцо дракона" in sent["keyboard"]
    assert "garden" in sent["keyboard"]


def test_epic_excluded_from_garden(db):
    from bot.handlers.commands import handle_garden
    # regular dragon + epic dragon both as UserDragon of same user
    reg = Dragon(name="Reg", rarity=1, steps_count=2, is_active=True, is_epic=False, egg_type="Обычное")
    epi = Dragon(name="Epi", rarity=1, steps_count=2, is_active=True, is_epic=True, egg_type="Тень")
    db.add_all([reg, epi])
    db.flush()
    u = User(vk_id=99, state="idle", current_dragon_id=reg.id, current_step=1)
    db.add(u)
    db.flush()
    db.add_all([
        UserDragon(user_id=99, dragon_id=reg.id, completed_at=""),
        UserDragon(user_id=99, dragon_id=epi.id, completed_at=""),
    ])
    db.commit()
    msgs = []
    handle_garden(u, db, lambda m, **k: msgs.append(m))
    joined = " ".join(msgs)
    assert "Обычное" in joined
    assert "Тень" not in joined


def test_epic_care_full_cycle_via_handlers(db):
    """Regression for review #1: show_care_action → handle_care_mode('norm') → handle_care_message.
    Guards the epic_care_state(stage_id, suffix) signature and the full care→finale path."""
    u, d = _epic(db, vk=30)
    u.epic_unlocked = True
    u.epic_dragon_id = d.id
    db.commit()
    st = EpicStage(stage_number=1, name="S1", cycles_count=1)
    db.add(st)
    db.flush()
    db.add(EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="кормить", order_in_cycle=0, crosses_norm=500))
    db.commit()
    epic_service.set_epic_name(db, 30, "Уголёк")
    care = epic_service.start_care(db, 30)

    def send(m, **k):
        pass

    show_care_action(u, db, send)
    assert u.state == f"epic_care_{care.stage_id}"

    handle_care_mode(u, "norm", db, send)
    assert u.state == f"epic_care_{care.stage_id}_norm"
    from bot.fsm import is_epic_care_waiting
    assert is_epic_care_waiting(u.state) is True

    handle_care_message(u, "вышито 500", _photos(), db, send)
    db.refresh(u)
    assert u.state == "await_epic_restart"
    assert u.stitches_balance == 1000


def test_epic_care_stage_up_via_handlers(db):
    """Completing stage 1 advances to stage 2 and shows the new stage (review #8)."""
    u, d = _epic(db, vk=31)
    u.epic_unlocked = True
    u.epic_dragon_id = d.id
    db.commit()
    st1 = EpicStage(stage_number=1, name="Малыш", cycles_count=1)
    st2 = EpicStage(stage_number=2, name="Подросток", cycles_count=1)
    db.add_all([st1, st2])
    db.flush()
    db.add(EpicStageAction(stage_id=st1.id, dragon_id=d.id, action_label="кормить", order_in_cycle=0, crosses_norm=100, timeout_hours=0))
    db.add(EpicStageAction(stage_id=st2.id, dragon_id=d.id, action_label="играть", order_in_cycle=0, crosses_norm=100, timeout_hours=0))
    db.commit()
    epic_service.set_epic_name(db, 31, "Уголёк")
    epic_service.start_care(db, 31)

    msgs = []

    def send(m, **k):
        msgs.append(m)

    show_care_action(u, db, send)
    handle_care_mode(u, "norm", db, send)
    handle_care_message(u, "вышито 100", _photos(), db, send)
    db.refresh(u)
    assert u.state == f"epic_care_{st2.id}"
    assert any("Подросток" in m for m in msgs)


def test_simple_action_shows_outcome(db):
    from models import EpicActionOutcome
    u, d = _epic(db, vk=45)
    u.epic_unlocked = True
    u.epic_dragon_id = d.id
    db.commit()
    st = EpicStage(stage_number=1, name="S1", cycles_count=1)
    db.add(st)
    db.flush()
    action = EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="кормить", order_in_cycle=0,
                             crosses_norm=100, timeout_hours=0, random_outcome=False)
    db.add(action)
    db.flush()
    db.add(EpicActionOutcome(action_id=action.id, polarity="positive",
                             moodlet_title="Сыт и счастлив", image_path="dragons/full.png"))
    db.add(EpicActionOutcome(action_id=action.id, polarity="negative"))
    db.commit()
    epic_service.set_epic_name(db, 45, "Уголёк")
    epic_service.start_care(db, 45)

    msgs = []

    def send(m, **k):
        msgs.append(m)

    show_care_action(u, db, send)
    handle_care_mode(u, "norm", db, send)
    handle_care_message(u, "вышито 100", _photos(), db, send)
    assert any("Сыт и счастлив" in m for m in msgs)


def _composite_setup(db, vk, with_steps, with_items):
    from models import EpicSubAction, EpicSubActionItem, EpicSubActionStep, EpicSubActionOutcome
    u, d = _epic(db, vk=vk)
    u.epic_unlocked = True
    u.epic_dragon_id = d.id
    db.commit()
    st = EpicStage(stage_number=1, name="S1", cycles_count=1)
    db.add(st)
    db.flush()
    action = EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="уход", order_in_cycle=0,
                             action_type="composite", timeout_hours=0)
    db.add(action)
    db.flush()
    sa = EpicSubAction(action_id=action.id, label="Расчесать", description="Ты берёшь щётку…",
                       confirm_button_label="🪮 Расчесать")
    db.add(sa)
    db.flush()
    for polarity in ("positive", "negative"):
        db.add(EpicSubActionOutcome(sub_action_id=sa.id, polarity=polarity, moodlet_title=f"m-{polarity}"))
    if with_items:
        it = ShopItem(name="Щётка", is_active=True, is_consumable=True)
        db.add(it)
        db.flush()
        db.add(EpicSubActionItem(sub_action_id=sa.id, item_id=it.id))
        db.add(UserInventory(user_id=vk, item_id=it.id, quantity=1))
    if with_steps:
        db.add(EpicSubActionStep(sub_action_id=sa.id, step_label="Шаг 1", order=0, crosses_norm=100))
    db.commit()
    epic_service.set_epic_name(db, vk, "Уголёк")
    epic_service.start_care(db, vk)
    return u, d, sa


def test_choose_sub_with_items_shows_confirm(db):
    from bot.handlers.epic_care import handle_choose_sub
    u, d, sa = _composite_setup(db, vk=40, with_steps=True, with_items=True)
    care = epic_service.get_care(db, 40)
    msgs = []
    sent = {}

    def send(m, **k):
        msgs.append(m)
        sent.update(k)

    handle_choose_sub(u, sa.id, db, send)
    db.refresh(u)
    assert u.state == f"epic_care_{care.stage_id}_sub_confirm"
    assert any("щётку" in m or "щётк" in m for m in msgs)
    assert "confirm_sub" in sent.get("keyboard", "")
    assert "🪮 Расчесать" in sent.get("keyboard", "")
    inv = db.query(UserInventory).filter(UserInventory.user_id == 40).first()
    assert inv is not None and inv.quantity == 1


def test_confirm_sub_consumes_and_goes_to_steps(db):
    from bot.handlers.epic_care import handle_choose_sub, handle_confirm_sub
    u, d, sa = _composite_setup(db, vk=41, with_steps=True, with_items=True)
    care = epic_service.get_care(db, 41)
    handle_choose_sub(u, sa.id, db, lambda m, **k: None)
    handle_confirm_sub(u, db, lambda m, **k: None)
    db.refresh(u)
    assert u.state == f"epic_care_{care.stage_id}_sub"
    inv = db.query(UserInventory).filter(UserInventory.user_id == 41).first()
    assert inv is None


def test_confirm_sub_no_steps_resolves_outcome(db):
    from bot.handlers.epic_care import handle_choose_sub, handle_confirm_sub
    u, d, sa = _composite_setup(db, vk=42, with_steps=False, with_items=True)
    handle_choose_sub(u, sa.id, db, lambda m, **k: None)
    msgs = []
    handle_confirm_sub(u, db, lambda m, **k: msgs.append(m))
    db.refresh(u)
    assert u.state == "await_epic_restart"
    care = epic_service.get_care(db, 42)
    assert care.current_sub_action_id is None
    inv = db.query(UserInventory).filter(UserInventory.user_id == 42).first()
    assert inv is None


def test_choose_sub_without_items_skips_confirm(db):
    from bot.handlers.epic_care import handle_choose_sub
    u, d, sa = _composite_setup(db, vk=43, with_steps=True, with_items=False)
    care = epic_service.get_care(db, 43)
    handle_choose_sub(u, sa.id, db, lambda m, **k: None)
    db.refresh(u)
    assert u.state == f"epic_care_{care.stage_id}_sub"

