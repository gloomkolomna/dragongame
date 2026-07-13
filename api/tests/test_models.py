from models import (
    Dragon, DragonStep, User, UserDragon, UserProgress,
    ShopItem, StageShopItem, UserInventory, SuspiciousReport,
    EpicStage, EpicStageAction, EpicCareState,
    StageChoiceBlock, StageChoiceOption, UserStageChoice, EpicMoodlet,
    CharacterAxis, CharacterBalance,
    EpicSubAction, EpicSubActionItem, EpicSubActionStep, EpicSubActionOutcome,
)


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


def test_dragon_is_epic_default(db):
    d = Dragon(name="Epic", rarity=1, steps_count=0, is_active=True)
    db.add(d)
    db.commit()
    assert d.is_epic is False


def test_dragon_legend_image_path(db):
    d = Dragon(name="Leg", rarity=3, steps_count=0, is_active=True, legend_image_path="dragons/leg_cover.png")
    db.add(d)
    db.commit()
    assert d.legend_image_path == "dragons/leg_cover.png"


def test_dragon_step_phase_default(db):
    d = Dragon(name="D", rarity=1, steps_count=0, is_active=True)
    db.add(d)
    db.flush()
    step = DragonStep(dragon_id=d.id, step_number=1)
    db.add(step)
    db.commit()
    assert step.phase == 0


def test_user_new_fields(db):
    user = User(vk_id=999, stitches_balance=1500, epic_unlocked=True, epic_dragon_id=5)
    db.add(user)
    db.commit()
    assert user.stitches_balance == 1500
    assert user.epic_unlocked is True
    assert user.epic_dragon_id == 5


def test_user_progress_epic_name(db):
    user = User(vk_id=1000)
    dragon = Dragon(name="E", rarity=1, steps_count=1, is_active=True)
    db.add(user)
    db.add(dragon)
    db.flush()
    up = UserProgress(user_id=user.vk_id, dragon_id=dragon.id, step_number=1, epic_name="Туманокрыл")
    db.add(up)
    db.commit()
    assert up.epic_name == "Туманокрыл"


def test_shop_item_crud(db):
    item = ShopItem(name="Potion", description="Healing", cost_stitches=500)
    db.add(item)
    db.commit()
    assert item.id is not None
    assert item.is_active is True


def test_stage_shop_item(db):
    item = ShopItem(name="Toy", cost_stitches=100)
    db.add(item)
    db.flush()
    link = StageShopItem(stage_key="epic:1", item_id=item.id, sort_order=1)
    db.add(link)
    db.commit()
    assert link.id is not None


def test_user_inventory(db):
    user = User(vk_id=2000)
    item = ShopItem(name="Book", cost_stitches=300)
    db.add(user)
    db.add(item)
    db.flush()
    inv = UserInventory(user_id=user.vk_id, item_id=item.id, quantity=2)
    db.add(inv)
    db.commit()
    assert inv.quantity == 2


def test_suspicious_report(db):
    user = User(vk_id=3000)
    dragon = Dragon(name="D", rarity=1, steps_count=1, is_active=True)
    db.add(user)
    db.add(dragon)
    db.flush()
    sr = SuspiciousReport(user_id=user.vk_id, dragon_id=dragon.id, step_number=1, declared_crosses=5000, normal_crosses=500, mode="norm", status="pending")
    db.add(sr)
    db.commit()
    assert sr.id is not None
    assert sr.status == "pending"


def test_epic_stage_crud(db):
    dragon = Dragon(name="E", rarity=1, steps_count=1, is_active=True, is_epic=True)
    db.add(dragon)
    db.flush()
    stage = EpicStage(dragon_id=dragon.id, stage_number=1, name="Вылупленное чудо")
    db.add(stage)
    db.commit()
    assert stage.id is not None


def test_epic_stage_action(db):
    dragon = Dragon(name="E", rarity=1, steps_count=1, is_active=True, is_epic=True)
    db.add(dragon)
    db.flush()
    stage = EpicStage(dragon_id=dragon.id, stage_number=1, name="Stage 1")
    db.add(stage)
    db.flush()
    action = EpicStageAction(dragon_id=dragon.id, stage_id=stage.id, action_label="Кормить", order_in_cycle=1)
    db.add(action)
    db.commit()
    assert action.id is not None


def test_epic_care_state(db):
    user = User(vk_id=4000)
    dragon = Dragon(name="E", rarity=1, steps_count=1, is_active=True)
    stage = EpicStage(dragon_id=1, stage_number=1, name="S1")
    db.add(user)
    db.add(dragon)
    db.add(stage)
    db.flush()
    ud = UserDragon(user_id=user.vk_id, dragon_id=dragon.id)
    db.add(ud)
    db.flush()
    cs = EpicCareState(user_dragon_id=ud.id, stage_id=stage.id, current_action_order=2)
    db.add(cs)
    db.commit()
    assert cs.current_action_order == 2
    assert cs.care_notified is False


def test_stage_choice_block(db):
    stage = EpicStage(dragon_id=1, stage_number=1, name="S1")
    db.add(stage)
    db.flush()
    block = StageChoiceBlock(stage_id=stage.id, block_key="diet", choice_type="single", min_picks=1, max_picks=1)
    db.add(block)
    db.commit()
    assert block.id is not None
    assert block.locked_after_done is True


def test_stage_choice_option(db):
    stage = EpicStage(dragon_id=1, stage_number=1, name="S1")
    db.add(stage)
    db.flush()
    block = StageChoiceBlock(stage_id=stage.id, block_key="diet", choice_type="single")
    db.add(block)
    db.flush()
    opt = StageChoiceOption(block_id=block.id, label="Всеядный", group="neutral")
    db.add(opt)
    db.commit()
    assert opt.id is not None


def test_user_stage_choice(db):
    user = User(vk_id=5000)
    dragon = Dragon(name="E", rarity=1, steps_count=1, is_active=True)
    stage = EpicStage(dragon_id=1, stage_number=1, name="S1")
    db.add(user)
    db.add(dragon)
    db.add(stage)
    db.flush()
    ud = UserDragon(user_id=user.vk_id, dragon_id=dragon.id)
    db.add(ud)
    db.flush()
    block = StageChoiceBlock(stage_id=stage.id, block_key="diet", choice_type="single")
    db.add(block)
    db.flush()
    opt = StageChoiceOption(block_id=block.id, label="Всеядный")
    db.add(opt)
    db.flush()
    usc = UserStageChoice(user_dragon_id=ud.id, block_id=block.id, option_id=opt.id)
    db.add(usc)
    db.commit()
    assert usc.id is not None


def test_epic_moodlet(db):
    user = User(vk_id=6000)
    dragon = Dragon(name="E", rarity=1, steps_count=1, is_active=True)
    stage = EpicStage(dragon_id=1, stage_number=1, name="S1")
    db.add(user)
    db.add(dragon)
    db.add(stage)
    db.flush()
    ud = UserDragon(user_id=user.vk_id, dragon_id=dragon.id)
    db.add(ud)
    db.flush()
    moodlet = EpicMoodlet(user_dragon_id=ud.id, key="first_cry", title="Первый крик", stage_id=stage.id)
    db.add(moodlet)
    db.commit()
    assert moodlet.id is not None


def test_character_axis(db):
    ax = CharacterAxis(positive_label="Добрый", negative_label="Злой", sort_order=1, is_active=True)
    db.add(ax)
    db.commit()
    assert ax.id is not None
    assert ax.positive_label == "Добрый"
    assert ax.negative_label == "Злой"


def test_character_balance(db):
    user = User(vk_id=7000)
    dragon = Dragon(name="F", rarity=1, steps_count=1, is_active=True)
    db.add(user)
    db.add(dragon)
    db.flush()
    ax = CharacterAxis(positive_label="Сильный", negative_label="Слабый")
    db.add(ax)
    db.flush()
    ud = UserDragon(user_id=user.vk_id, dragon_id=dragon.id)
    db.add(ud)
    db.flush()
    cb = CharacterBalance(user_dragon_id=ud.id, axis_id=ax.id, score=5)
    db.add(cb)
    db.commit()
    assert cb.id is not None
    assert cb.score == 5


def test_epic_sub_action(db):
    user = User(vk_id=8000)
    dragon = Dragon(name="G", rarity=1, steps_count=1, is_active=True, is_epic=True)
    stage = EpicStage(dragon_id=1, stage_number=1, name="S1")
    db.add(user)
    db.add(dragon)
    db.add(stage)
    db.flush()
    action = EpicStageAction(dragon_id=dragon.id, stage_id=stage.id, action_label="Выходной", action_type="composite")
    db.add(action)
    db.flush()
    ax = CharacterAxis(positive_label="Весёлый", negative_label="Грустный")
    db.add(ax)
    db.flush()
    sa = EpicSubAction(action_id=action.id, label="На рыбалку", character_axis_id=ax.id)
    db.add(sa)
    db.commit()
    assert sa.id is not None
    assert sa.character_axis_id == ax.id


def test_epic_sub_action_step(db):
    user, dragon, stage = _epic_fixture(db)
    action = EpicStageAction(dragon_id=dragon.id, stage_id=stage.id, action_label="Test", action_type="composite")
    db.add(action)
    db.flush()
    sa = EpicSubAction(action_id=action.id, label="Поддействие")
    db.add(sa)
    db.flush()
    step = EpicSubActionStep(sub_action_id=sa.id, step_label="Шаг 1", order=1, crosses_norm=500)
    db.add(step)
    db.commit()
    assert step.id is not None
    assert step.crosses_norm == 500


def test_epic_sub_action_outcome(db):
    user, dragon, stage = _epic_fixture(db)
    action = EpicStageAction(dragon_id=dragon.id, stage_id=stage.id, action_label="Test", action_type="composite")
    db.add(action)
    db.flush()
    sa = EpicSubAction(action_id=action.id, label="Поддействие")
    db.add(sa)
    db.flush()
    o1 = EpicSubActionOutcome(sub_action_id=sa.id, polarity="positive", moodlet_title="Ура!")
    o2 = EpicSubActionOutcome(sub_action_id=sa.id, polarity="negative", moodlet_title="Увы")
    db.add(o1)
    db.add(o2)
    db.commit()
    assert o1.id is not None
    assert o2.id is not None
    assert o1.polarity == "positive"


def test_shop_item_is_consumable(db):
    item = ShopItem(name="Инструмент", is_consumable=False, is_active=True)
    db.add(item)
    db.commit()
    assert item.is_consumable is False


def test_epic_care_state_sub_fields(db):
    user, dragon, stage = _epic_fixture(db)
    action = EpicStageAction(dragon_id=dragon.id, stage_id=stage.id, action_label="Test", action_type="composite")
    db.add(action)
    db.flush()
    sa = EpicSubAction(action_id=action.id, label="Поддействие")
    db.add(sa)
    db.flush()
    ud = UserDragon(user_id=user.vk_id, dragon_id=dragon.id)
    db.add(ud)
    db.flush()
    care = EpicCareState(user_dragon_id=ud.id, stage_id=stage.id, current_sub_action_id=sa.id, current_step_order=2, sub_had_penalty=True)
    db.add(care)
    db.commit()
    assert care.current_sub_action_id == sa.id
    assert care.current_step_order == 2
    assert care.sub_had_penalty is True


def _epic_fixture(db):
    user = User(vk_id=9000)
    dragon = Dragon(name="H", rarity=1, steps_count=1, is_active=True, is_epic=True)
    stage = EpicStage(dragon_id=1, stage_number=1, name="S1")
    for obj in [user, dragon, stage]:
        db.add(obj)
    db.flush()
    return user, dragon, stage
