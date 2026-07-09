from models import (
    User, Dragon, DragonStep, UserDragon, UserProgress,
    EpicStage, EpicStageAction, EpicActionItem, ShopItem, UserInventory,
    EpicCareState, EpicMoodlet,
)
from services import epic_service
from bot.services.grow_service import complete_step


def _epic_dragon(db, name="Epic", steps=2):
    d = Dragon(name=name, rarity=1, steps_count=steps, is_active=True, is_epic=True, egg_type="Тень")
    db.add(d)
    db.flush()
    for i in range(1, steps + 1):
        db.add(DragonStep(dragon_id=d.id, step_number=i, phase=0, crosses_norm=1000))
    db.commit()
    return d


def _stage(db, number=1, cycles=1, actions=1, action_timeout_h=0, dragon_id=None):
    st = EpicStage(stage_number=number, name=f"S{number}", cycles_count=cycles)
    db.add(st)
    db.flush()
    acts = []
    for i in range(actions):
        a = EpicStageAction(dragon_id=dragon_id, stage_id=st.id, action_label=f"act{i}", order_in_cycle=i, crosses_norm=1000,
                            timeout_hours=action_timeout_h, timeout_minutes=0)
        db.add(a)
        acts.append(a)
    db.commit()
    return st, acts


def _regular_completed(db, vk_id):
    reg = Dragon(name="Reg", rarity=1, steps_count=1, is_active=True, is_epic=False)
    db.add(reg)
    db.flush()
    db.add(UserDragon(user_id=vk_id, dragon_id=reg.id, completed_at="2026-01-01T00:00:00"))
    db.commit()
    return reg


def test_maybe_spawn_first_epic_idempotent(db):
    db.add(User(vk_id=1, epic_unlocked=False))
    d = _epic_dragon(db)
    _regular_completed(db, 1)
    got = epic_service.maybe_spawn_first_epic(db, 1)
    assert got is not None and got.id == d.id
    u = db.query(User).filter(User.vk_id == 1).first()
    assert u.epic_unlocked is True
    assert u.epic_dragon_id == d.id
    assert epic_service.maybe_spawn_first_epic(db, 1) is None


def test_maybe_spawn_requires_completed_dragon(db):
    db.add(User(vk_id=20, epic_unlocked=False))
    _epic_dragon(db)
    assert epic_service.maybe_spawn_first_epic(db, 20) is None


def test_spawn_no_pool(db):
    db.add(User(vk_id=2))
    db.commit()
    assert epic_service.maybe_spawn_first_epic(db, 2) is None


def test_egg_hatch_and_name(db):
    db.add(User(vk_id=3, epic_unlocked=False))
    d = _epic_dragon(db, steps=2)
    epic_service.spawn_random_epic(db, 3)
    assert epic_service.is_egg_hatched(db, 3) is False
    complete_step(db, 3, d.id, 1)
    complete_step(db, 3, d.id, 2)
    assert epic_service.is_egg_hatched(db, 3) is True
    epic_service.set_epic_name(db, 3, "Уголёк")
    assert epic_service.get_epic_name(db, 3) == "Уголёк"


def test_advance_cycle_to_finale(db):
    db.add(User(vk_id=4, epic_unlocked=False))
    d = _epic_dragon(db)
    epic_service.spawn_random_epic(db, 4)
    st, _ = _stage(db, number=1, cycles=2, actions=2, dragon_id=d.id)
    care = epic_service.start_care(db, 4)
    assert care.stage_id == st.id

    assert epic_service.advance_care(db, care)["event"] == "next_action"
    assert care.current_action_order == 1
    assert epic_service.advance_care(db, care)["event"] == "cycle_done"
    assert care.cycles_completed == 1
    assert epic_service.advance_care(db, care)["event"] == "next_action"
    assert epic_service.advance_care(db, care)["event"] == "finale"


def test_advance_stage_up(db):
    db.add(User(vk_id=5))
    d = _epic_dragon(db)
    epic_service.spawn_random_epic(db, 5)
    _stage(db, number=1, cycles=1, actions=1, dragon_id=d.id)
    st2, _ = _stage(db, number=2, cycles=1, actions=1, dragon_id=d.id)
    care = epic_service.start_care(db, 5)
    e = epic_service.advance_care(db, care)
    assert e["event"] == "stage_up"
    assert care.stage_id == st2.id


def test_missing_items_and_character(db):
    db.add(User(vk_id=6, stitches_balance=0))
    d = _epic_dragon(db)
    epic_service.spawn_random_epic(db, 6)
    st, _ = _stage(db, number=1, cycles=1, actions=0, dragon_id=d.id)
    it = ShopItem(name="Бутылочка", is_active=True, character_effect="заботливый")
    db.add(it)
    db.flush()
    a = EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="кормить", order_in_cycle=0, crosses_norm=1000)
    db.add(a)
    db.flush()
    db.add(EpicActionItem(action_id=a.id, item_id=it.id))
    db.commit()

    epic_service.start_care(db, 6)
    assert len(epic_service.missing_action_items(db, 6, a.id)) == 1
    db.add(UserInventory(user_id=6, item_id=it.id, quantity=1))
    db.commit()
    assert epic_service.missing_action_items(db, 6, a.id) == []
    assert epic_service.character_effects(db, 6) == ["заботливый"]


def test_restart_same_resets_slot(db):
    db.add(User(vk_id=7))
    d = _epic_dragon(db)
    epic_service.spawn_random_epic(db, 7)
    ud = epic_service.get_epic_user_dragon(db, 7)
    ud.completed_at = "2026-01-01T00:00:00"
    db.commit()
    dragon, others = epic_service.restart_epic(db, 7, "same")
    assert dragon.id == d.id
    assert others is False
    ud2 = epic_service.get_epic_user_dragon(db, 7)
    assert ud2.completed_at == ""


def test_care_timeout_gating(db):
    db.add(User(vk_id=8))
    d = _epic_dragon(db)
    epic_service.spawn_random_epic(db, 8)
    st, _ = _stage(db, number=1, cycles=3, actions=1, action_timeout_h=24, dragon_id=d.id)
    care = epic_service.start_care(db, 8)
    epic_service.advance_care(db, care)
    assert epic_service.get_care_remaining(db, care) is not None


def test_actions_unique_per_dragon(db):
    db.add(User(vk_id=9))
    d1 = _epic_dragon(db, name="D1")
    d2 = _epic_dragon(db, name="D2")
    st = EpicStage(stage_number=1, name="S1", cycles_count=1)
    db.add(st)
    db.flush()
    db.add(EpicStageAction(dragon_id=d1.id, stage_id=st.id, action_label="d1act", order_in_cycle=0, crosses_norm=100))
    db.add(EpicStageAction(dragon_id=d2.id, stage_id=st.id, action_label="d2act", order_in_cycle=0, crosses_norm=100))
    db.commit()

    a1 = epic_service.get_stage_actions(db, st.id, d1.id)
    a2 = epic_service.get_stage_actions(db, st.id, d2.id)
    assert [a.action_label for a in a1] == ["d1act"]
    assert [a.action_label for a in a2] == ["d2act"]

    epic_service.spawn_random_epic(db, 9, exclude_id=d2.id)
    care = epic_service.start_care(db, 9)
    cur = epic_service.get_current_action(db, care)
    assert cur.action_label == "d1act"
