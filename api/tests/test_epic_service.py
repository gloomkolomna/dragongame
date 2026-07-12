from models import (
    User, Dragon, DragonStep, UserDragon, UserProgress,
    EpicStage, EpicStageAction, EpicActionItem, ShopItem, UserInventory,
    EpicCareState, EpicMoodlet,
    CharacterAxis, CharacterBalance,
    EpicSubAction, EpicSubActionItem, EpicSubActionStep, EpicSubActionOutcome,
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


def test_get_epic_name_for_multiple(db):
    db.add(User(vk_id=33, epic_unlocked=True))
    e1 = _epic_dragon(db, name="E1", steps=1)
    e2 = _epic_dragon(db, name="E2", steps=1)
    db.add(UserDragon(user_id=33, dragon_id=e1.id, completed_at="2026-01-01T00:00:00"))
    db.add(UserDragon(user_id=33, dragon_id=e2.id, completed_at=""))
    u = db.query(User).filter(User.vk_id == 33).first()
    u.epic_dragon_id = e2.id
    db.add(UserProgress(user_id=33, dragon_id=e1.id, step_number=0, completed=False, epic_name="Старый"))
    db.commit()
    epic_service.set_epic_name(db, 33, "Новый")

    assert epic_service.get_epic_name_for(db, 33, e1.id) == "Старый"
    assert epic_service.get_epic_name_for(db, 33, e2.id) == "Новый"
    assert epic_service.get_epic_name(db, 33) == "Новый"
    assert epic_service.get_epic_name_for(db, 33, 99999) == ""


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
    it = ShopItem(name="Бутылочка", is_active=True)
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


def test_composite_sub_actions(db):
    user = User(vk_id=100, stitches_balance=500)
    d = _epic_dragon(db)
    db.add(user)
    db.commit()
    epic_service.spawn_random_epic(db, 100)
    st, _ = _stage(db, number=1, cycles=1, actions=0, dragon_id=d.id)
    ax = CharacterAxis(positive_label="Смелый", negative_label="Трусливый")
    db.add(ax)
    db.flush()
    action = EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="Выходной", order_in_cycle=0, action_type="composite")
    db.add(action)
    db.flush()
    sa = EpicSubAction(action_id=action.id, label="На рыбалку", character_axis_id=ax.id)
    db.add(sa)
    db.flush()
    db.add(EpicSubActionStep(sub_action_id=sa.id, step_label="Шаг 1", order=1, crosses_norm=500, timeout_hours=0, timeout_minutes=0))
    db.add(EpicSubActionStep(sub_action_id=sa.id, step_label="Шаг 2", order=2, crosses_norm=300, timeout_hours=0, timeout_minutes=0))
    db.add(EpicSubActionOutcome(sub_action_id=sa.id, polarity="positive", moodlet_title="Поймал!", moodlet_text="Улов отличный"))
    db.add(EpicSubActionOutcome(sub_action_id=sa.id, polarity="negative", moodlet_title="Пусто", moodlet_text="Ничего не клюнуло"))
    db.commit()

    subs = epic_service.get_sub_actions(db, action.id)
    assert len(subs) == 1
    assert subs[0].label == "На рыбалку"

    steps = epic_service.get_sub_steps(db, sa.id)
    assert len(steps) == 2
    assert steps[0].step_label == "Шаг 1"

    outcomes = epic_service.get_outcomes(db, sa.id)
    assert len(outcomes) == 2

    care = epic_service.start_care(db, 100)
    assert care is not None

    missing = epic_service.missing_sub_items(db, 100, sa.id)
    assert len(missing) == 0

    epic_service.start_sub_action(db, care, sa.id, 100)
    assert care.current_sub_action_id == sa.id
    assert care.current_step_order == 0
    assert care.sub_had_penalty is False

    step = epic_service.get_current_sub_step(db, care)
    assert step is not None
    assert step.step_label == "Шаг 1"

    result = epic_service.advance_sub_step(db, care)
    assert result == "next_step"
    assert care.current_step_order == 1

    step2 = epic_service.get_current_sub_step(db, care)
    assert step2.step_label == "Шаг 2"

    result = epic_service.advance_sub_step(db, care)
    assert result == "outcome"
    assert care.current_step_order == 2


def test_roll_outcome_polarity_neutral(db):
    user = User(vk_id=101, stitches_balance=500)
    d = _epic_dragon(db)
    db.add(user)
    db.commit()
    epic_service.spawn_random_epic(db, 101)
    st, _ = _stage(db, number=1, cycles=1, actions=0, dragon_id=d.id)
    ax = CharacterAxis(positive_label="Добрый", negative_label="Злой")
    db.add(ax)
    db.flush()
    action = EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="Test", order_in_cycle=0, action_type="composite")
    db.add(action)
    db.flush()
    sa = EpicSubAction(action_id=action.id, label="Sub", character_axis_id=ax.id)
    db.add(sa)
    db.commit()

    care = epic_service.start_care(db, 101)
    epic_service.start_sub_action(db, care, sa.id, 101)
    care.sub_had_penalty = False
    db.commit()

    import random
    import services.epic_service as es

    original = random.random
    try:
        random.random = lambda: 0.4
        assert es.roll_outcome_polarity(db, care) == "positive"
        random.random = lambda: 0.6
        assert es.roll_outcome_polarity(db, care) == "negative"
    finally:
        random.random = original


def test_consume_sub_items_respects_is_consumable(db):
    user = User(vk_id=102, stitches_balance=500)
    d = _epic_dragon(db)
    db.add(user)
    db.commit()
    epic_service.spawn_random_epic(db, 102)
    st, _ = _stage(db, number=1, cycles=1, actions=0, dragon_id=d.id)
    it_consumable = ShopItem(name="Билет", is_active=True, is_consumable=True)
    it_tool = ShopItem(name="Удочка", is_active=True, is_consumable=False)
    db.add(it_consumable)
    db.add(it_tool)
    db.flush()
    action = EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="Test", order_in_cycle=0, action_type="composite")
    db.add(action)
    db.flush()
    sa = EpicSubAction(action_id=action.id, label="Sub")
    db.add(sa)
    db.flush()
    db.add(EpicSubActionItem(sub_action_id=sa.id, item_id=it_consumable.id))
    db.add(EpicSubActionItem(sub_action_id=sa.id, item_id=it_tool.id))
    db.add(UserInventory(user_id=102, item_id=it_consumable.id, quantity=1))
    db.add(UserInventory(user_id=102, item_id=it_tool.id, quantity=1))
    db.commit()

    care = epic_service.start_care(db, 102)
    epic_service.start_sub_action(db, care, sa.id, 102)

    inv_consumable = db.query(UserInventory).filter(UserInventory.user_id == 102, UserInventory.item_id == it_consumable.id).first()
    inv_tool = db.query(UserInventory).filter(UserInventory.user_id == 102, UserInventory.item_id == it_tool.id).first()
    assert inv_consumable is None
    assert inv_tool is not None
    assert inv_tool.quantity == 1


def test_character_summary(db):
    from services.character_service import character_summary, upsert_balance, get_axes
    user = User(vk_id=200)
    dragon = Dragon(name="C", rarity=1, steps_count=1, is_active=True, is_epic=True)
    db.add(user)
    db.add(dragon)
    db.flush()
    ax1 = CharacterAxis(positive_label="Добрый", negative_label="Злой", is_active=True)
    ax2 = CharacterAxis(positive_label="Сильный", negative_label="Слабый", is_active=True)
    db.add(ax1)
    db.add(ax2)
    db.flush()
    ud = UserDragon(user_id=user.vk_id, dragon_id=dragon.id)
    db.add(ud)
    db.flush()
    db.commit()

    upsert_balance(db, ud.id, ax1.id, 3)
    upsert_balance(db, ud.id, ax2.id, -2)

    summary = character_summary(db, ud.id)
    assert len(summary) == 2
    assert summary[0] == {"axis": "Добрый", "label": "Добрый", "polarity": "positive"}
    assert summary[1] == {"axis": "Слабый", "label": "Слабый", "polarity": "negative"}
