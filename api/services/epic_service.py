"""Epic dragon service — spawn, naming, egg/hatch, care state. Pure DB, no VK."""

import random
from datetime import datetime, timedelta
from models import (
    User, Dragon, UserDragon, UserProgress, DragonStep,
    EpicStage, EpicStageAction, EpicActionItem, EpicCareState,
    UserInventory, EpicMoodlet, ShopItem,
    CharacterAxis, CharacterBalance,
    EpicSubAction, EpicSubActionItem, EpicSubActionStep, EpicSubActionOutcome,
)


# ─── Spawn ───

def get_epic_pool(db, exclude_id=None):
    q = db.query(Dragon).filter(Dragon.is_epic == True)
    if exclude_id:
        q = q.filter(Dragon.id != exclude_id)
    return q.all()


def spawn_random_epic(db, vk_id, exclude_id=None):
    pool = get_epic_pool(db, exclude_id=exclude_id)
    if not pool and exclude_id:
        pool = get_epic_pool(db)
    if not pool:
        return None
    dragon = random.choice(pool)
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        return None
    existing = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon.id
    ).first()
    if not existing:
        db.add(UserDragon(user_id=vk_id, dragon_id=dragon.id, completed_at=""))
    user.epic_unlocked = True
    user.epic_dragon_id = dragon.id
    db.commit()
    return dragon


def maybe_spawn_first_epic(db, vk_id):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or user.epic_unlocked:
        return None
    if not get_epic_pool(db):
        return None
    completed = (
        db.query(UserDragon)
        .join(Dragon, Dragon.id == UserDragon.dragon_id)
        .filter(
            UserDragon.user_id == vk_id,
            UserDragon.completed_at != "",
            Dragon.is_epic == False,
        )
        .first()
    )
    if not completed:
        return None
    return spawn_random_epic(db, vk_id)


# ─── Epic dragon accessors ───

def get_epic_dragon(db, vk_id):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or not user.epic_dragon_id:
        return None
    return db.query(Dragon).filter(Dragon.id == user.epic_dragon_id).first()


def get_epic_user_dragon(db, vk_id):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or not user.epic_dragon_id:
        return None
    return db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == user.epic_dragon_id
    ).first()


# ─── Name ───

def set_epic_name(db, vk_id, name):
    dragon = get_epic_dragon(db, vk_id)
    if not dragon:
        return
    row = db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == dragon.id,
        UserProgress.step_number == 0,
    ).first()
    if row:
        row.epic_name = name
    else:
        db.add(UserProgress(
            user_id=vk_id, dragon_id=dragon.id, step_number=0,
            completed=False, epic_name=name,
        ))
    db.commit()


def get_epic_name(db, vk_id):
    dragon = get_epic_dragon(db, vk_id)
    if not dragon:
        return ""
    row = db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == dragon.id,
        UserProgress.step_number == 0,
    ).first()
    return row.epic_name if row and row.epic_name else ""


def get_epic_name_for(db, vk_id, dragon_id):
    row = db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == dragon_id,
        UserProgress.step_number == 0,
    ).first()
    return row.epic_name if row and row.epic_name else ""


# ─── Egg / hatch ───

def egg_completed_count(db, vk_id):
    dragon = get_epic_dragon(db, vk_id)
    if not dragon:
        return 0
    return db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == dragon.id,
        UserProgress.step_number > 0,
        UserProgress.completed == True,
    ).count()


def egg_total(db, vk_id):
    dragon = get_epic_dragon(db, vk_id)
    return dragon.steps_count if dragon else 0


def is_egg_hatched(db, vk_id):
    total = egg_total(db, vk_id)
    if total <= 0:
        return False
    return egg_completed_count(db, vk_id) >= total


# ─── Care state ───

def get_care(db, vk_id):
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return None
    return db.query(EpicCareState).filter(EpicCareState.user_dragon_id == ud.id).first()


def first_stage(db):
    return db.query(EpicStage).order_by(EpicStage.stage_number, EpicStage.id).first()


def max_stage_number(db):
    stages = db.query(EpicStage).all()
    return max((s.stage_number for s in stages), default=0)


def start_care(db, vk_id):
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return None
    existing = db.query(EpicCareState).filter(EpicCareState.user_dragon_id == ud.id).first()
    if existing:
        return existing
    stage = first_stage(db)
    if not stage:
        return None
    care = EpicCareState(
        user_dragon_id=ud.id, stage_id=stage.id,
        current_action_order=0, cycles_completed=0,
        next_action_at=None, care_notified=False,
    )
    db.add(care)
    db.commit()
    return care


# ─── Care cycle ───

def get_stage(db, stage_id):
    return db.query(EpicStage).filter(EpicStage.id == stage_id).first()


def care_dragon_id(db, care):
    if not care:
        return None
    ud = db.query(UserDragon).filter(UserDragon.id == care.user_dragon_id).first()
    return ud.dragon_id if ud else None


def get_stage_actions(db, stage_id, dragon_id):
    return (
        db.query(EpicStageAction)
        .filter(EpicStageAction.stage_id == stage_id, EpicStageAction.dragon_id == dragon_id)
        .order_by(EpicStageAction.order_in_cycle, EpicStageAction.id)
        .all()
    )


def get_current_action(db, care):
    if not care or not care.stage_id:
        return None
    dragon_id = care_dragon_id(db, care)
    if not dragon_id:
        return None
    actions = get_stage_actions(db, care.stage_id, dragon_id)
    if not actions:
        return None
    idx = care.current_action_order or 0
    if idx < 0 or idx >= len(actions):
        return None
    return actions[idx]


def action_items(db, action_id):
    ids = [ai.item_id for ai in db.query(EpicActionItem).filter(EpicActionItem.action_id == action_id).all()]
    if not ids:
        return []
    return db.query(ShopItem).filter(ShopItem.id.in_(ids)).all()


def has_action_items(db, action_id) -> bool:
    return db.query(EpicActionItem).filter(EpicActionItem.action_id == action_id).first() is not None


def has_non_optional_items(db, action_id) -> bool:
    ids = [ai.item_id for ai in db.query(EpicActionItem).filter(EpicActionItem.action_id == action_id).all()]
    if not ids:
        return False
    return db.query(ShopItem).filter(ShopItem.id.in_(ids), ShopItem.is_optional == False).first() is not None


def consume_action_items(db, vk_id, action_id):
    items = action_items(db, action_id)
    for item in items:
        inv = db.query(UserInventory).filter(
            UserInventory.user_id == vk_id,
            UserInventory.item_id == item.id,
        ).first()
        if inv:
            if inv.quantity > 1:
                inv.quantity -= 1
            else:
                db.delete(inv)
    db.commit()


def consume_owned_action_items(db, vk_id, action_id):
    """Consume only the items the user actually owns (respects optional flag)."""
    items = action_items(db, action_id)
    for item in items:
        inv = db.query(UserInventory).filter(
            UserInventory.user_id == vk_id,
            UserInventory.item_id == item.id,
        ).first()
        if inv:
            if inv.quantity > 1:
                inv.quantity -= 1
            else:
                db.delete(inv)
    db.commit()


def missing_action_items(db, vk_id, action_id):
    owned = {
        inv.item_id for inv in db.query(UserInventory).filter(UserInventory.user_id == vk_id).all()
    }
    return [
        it for it in action_items(db, action_id)
        if it.id not in owned and not it.is_optional
    ]


def missing_optional_action_items(db, vk_id, action_id):
    owned = {
        inv.item_id for inv in db.query(UserInventory).filter(UserInventory.user_id == vk_id).all()
    }
    return [
        it for it in action_items(db, action_id)
        if it.id not in owned and it.is_optional
    ]


def set_care_timeout(db, care, action):
    minutes = (action.timeout_hours or 0) * 60 + (action.timeout_minutes or 0)
    if minutes <= 0:
        care.next_action_at = None
    else:
        care.next_action_at = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S")
    care.care_notified = False
    db.commit()


def get_care_remaining(db, care):
    if not care or not care.next_action_at:
        return None
    try:
        available = datetime.fromisoformat(care.next_action_at)
    except (ValueError, TypeError):
        return None
    remaining = available - datetime.now()
    if remaining.total_seconds() <= 0:
        return None
    return remaining


def advance_care(db, care):
    """Advance past the just-completed action. Returns event dict."""
    stage = get_stage(db, care.stage_id)
    actions = get_stage_actions(db, care.stage_id, care_dragon_id(db, care))
    completed_action = get_current_action(db, care)
    n = len(actions)
    care.current_action_order = (care.current_action_order or 0) + 1
    event = {"event": "next_action"}

    if care.current_action_order >= n:
        care.current_action_order = 0
        care.cycles_completed = (care.cycles_completed or 0) + 1
        if stage and care.cycles_completed >= (stage.cycles_count or 1):
            nxt = (
                db.query(EpicStage)
                .filter(EpicStage.stage_number > stage.stage_number)
                .order_by(EpicStage.stage_number, EpicStage.id)
                .first()
            )
            if nxt:
                care.stage_id = nxt.id
                care.cycles_completed = 0
                care.current_action_order = 0
                event = {"event": "stage_up", "stage": nxt, "prev_stage": stage}
            else:
                event = {"event": "finale", "stage": stage}
        else:
            event = {"event": "cycle_done", "stage": stage}

    timeout_action = completed_action or get_current_action(db, care)
    if timeout_action:
        set_care_timeout(db, care, timeout_action)
    else:
        care.next_action_at = None
        care.care_notified = False
    db.commit()
    return event


# ─── Composite actions (sub-actions → steps → outcome) ───

def get_sub_actions(db, action_id):
    return (
        db.query(EpicSubAction)
        .filter(EpicSubAction.action_id == action_id)
        .order_by(EpicSubAction.order_in_sub, EpicSubAction.id)
        .all()
    )


def get_sub_action(db, sub_id):
    return db.query(EpicSubAction).filter(EpicSubAction.id == sub_id).first()


def get_sub_steps(db, sub_id):
    return (
        db.query(EpicSubActionStep)
        .filter(EpicSubActionStep.sub_action_id == sub_id)
        .order_by(EpicSubActionStep.order, EpicSubActionStep.id)
        .all()
    )


def get_outcomes(db, sub_id):
    return db.query(EpicSubActionOutcome).filter(EpicSubActionOutcome.sub_action_id == sub_id).all()


def get_current_sub_step(db, care):
    if not care or not care.current_sub_action_id:
        return None
    steps = get_sub_steps(db, care.current_sub_action_id)
    idx = care.current_step_order or 0
    if idx < 0 or idx >= len(steps):
        return None
    return steps[idx]


def sub_action_items(db, sub_id):
    ids = [
        sai.item_id
        for sai in db.query(EpicSubActionItem).filter(EpicSubActionItem.sub_action_id == sub_id).all()
    ]
    if not ids:
        return []
    return db.query(ShopItem).filter(ShopItem.id.in_(ids)).all()


def missing_sub_items(db, vk_id, sub_id):
    owned = {inv.item_id for inv in db.query(UserInventory).filter(UserInventory.user_id == vk_id).all()}
    return [it for it in sub_action_items(db, sub_id) if it.id not in owned]


def consume_sub_items(db, vk_id, sub_id):
    for item in sub_action_items(db, sub_id):
        if not item.is_consumable:
            continue
        inv = db.query(UserInventory).filter(
            UserInventory.user_id == vk_id,
            UserInventory.item_id == item.id,
        ).first()
        if inv:
            if inv.quantity > 1:
                inv.quantity -= 1
            else:
                db.delete(inv)
    db.commit()


def start_sub_action(db, care, sub_action_id, vk_id):
    care.current_sub_action_id = sub_action_id
    care.current_step_order = 0
    care.sub_had_penalty = False
    consume_sub_items(db, vk_id, sub_action_id)
    db.commit()


def sub_has_items(db, sub_id) -> bool:
    return db.query(EpicSubActionItem).filter(EpicSubActionItem.sub_action_id == sub_id).first() is not None


def select_sub_action(db, care, sub_action_id):
    care.current_sub_action_id = sub_action_id
    care.current_step_order = 0
    care.sub_had_penalty = False
    db.commit()


def advance_sub_step(db, care):
    steps = get_sub_steps(db, care.current_sub_action_id)
    care.current_step_order = (care.current_step_order or 0) + 1
    db.commit()
    if care.current_step_order >= len(steps):
        return "outcome"
    return "next_step"


def roll_outcome_polarity(db, care):
    balances = db.query(CharacterBalance).filter(
        CharacterBalance.user_dragon_id == care.user_dragon_id
    ).all()
    pos = sum(max(b.score or 0, 0) for b in balances)
    neg = sum(max(-(b.score or 0), 0) for b in balances)
    if pos + neg > 0:
        char_component = pos / (pos + neg)
    else:
        char_component = 0.5
    penalty_mult = 0.5 if care.sub_had_penalty else 1.0
    chance = max(0.05, min(0.95, char_component * penalty_mult))
    return "positive" if random.random() < chance else "negative"


def _award_outcome_moodlet(db, user_dragon_id, polarity, outcome):
    key = f"sub:{outcome.sub_action_id}:{polarity}"
    existing = db.query(EpicMoodlet).filter(
        EpicMoodlet.user_dragon_id == user_dragon_id,
        EpicMoodlet.key == key,
    ).first()
    if not existing:
        sub_action = get_sub_action(db, outcome.sub_action_id)
        db.add(EpicMoodlet(
            user_dragon_id=user_dragon_id,
            key=key,
            title=outcome.moodlet_title,
            polarity=polarity,
            text=outcome.moodlet_text,
            axis_id=sub_action.character_axis_id if sub_action else None,
        ))
        db.commit()


def resolve_outcome(db, vk_id, care, sub_action):
    polarity = roll_outcome_polarity(db, care)
    outcome = db.query(EpicSubActionOutcome).filter(
        EpicSubActionOutcome.sub_action_id == sub_action.id,
        EpicSubActionOutcome.polarity == polarity,
    ).first()
    if not outcome:
        outcome = db.query(EpicSubActionOutcome).filter(
            EpicSubActionOutcome.sub_action_id == sub_action.id,
        ).first()
    if outcome:
        _award_outcome_moodlet(db, care.user_dragon_id, polarity, outcome)
    from services.character_service import upsert_balance
    if sub_action.character_axis_id:
        delta = 1 if polarity == "positive" else -1
        upsert_balance(db, care.user_dragon_id, sub_action.character_axis_id, delta)
    care.current_sub_action_id = None
    care.current_step_order = 0
    care.sub_had_penalty = False
    db.commit()
    return outcome, polarity


# ─── Moodlets ───


def get_moodlets(db, vk_id):
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return []
    return (
        db.query(EpicMoodlet)
        .filter(EpicMoodlet.user_dragon_id == ud.id)
        .order_by(EpicMoodlet.id)
        .all()
    )


def _reset_epic_slot(db, vk_id, target_id):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        return
    user.epic_dragon_id = target_id
    user.epic_unlocked = True
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == target_id
    ).first()
    if not ud:
        db.add(UserDragon(user_id=vk_id, dragon_id=target_id, completed_at=""))
        db.commit()
        return
    ud.completed_at = ""
    db.query(UserProgress).filter(
        UserProgress.user_id == vk_id, UserProgress.dragon_id == target_id
    ).delete(synchronize_session=False)
    db.query(EpicCareState).filter(EpicCareState.user_dragon_id == ud.id).delete(synchronize_session=False)
    db.query(EpicMoodlet).filter(EpicMoodlet.user_dragon_id == ud.id).delete(synchronize_session=False)
    db.query(CharacterBalance).filter(CharacterBalance.user_dragon_id == ud.id).delete(synchronize_session=False)
    db.commit()


def restart_epic(db, vk_id, mode):
    prev = get_epic_dragon(db, vk_id)
    prev_id = prev.id if prev else None
    if mode == "same" and prev_id:
        target_id = prev_id
        had_others = False
    else:
        pool = get_epic_pool(db, exclude_id=prev_id)
        had_others = len(pool) > 0
        if pool:
            target_id = random.choice(pool).id
        elif prev_id:
            target_id = prev_id
        else:
            full = get_epic_pool(db)
            if not full:
                return None, False
            target_id = random.choice(full).id
    _reset_epic_slot(db, vk_id, target_id)
    return db.query(Dragon).filter(Dragon.id == target_id).first(), had_others

