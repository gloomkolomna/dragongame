"""Epic dragon service — spawn, naming, egg/hatch, care state. Pure DB, no VK."""

import random
from datetime import datetime, timedelta
from models import (
    User, Dragon, UserDragon, UserProgress, DragonStep,
    EpicStage, EpicStageAction, EpicActionItem, EpicCareState,
    UserInventory, EpicMoodlet, ShopItem,
    CharacterAxis, CharacterBalance,
    EpicSubAction, EpicSubActionItem, EpicSubActionStep, EpicSubActionOutcome,
    EpicActionOutcome, UserItemUsage, StageShopItem,
)


# ─── Spawn ───

def has_completed_regular_dragon(db, vk_id):
    return db.query(UserDragon).join(Dragon).filter(
        UserDragon.user_id == vk_id,
        UserDragon.completed_at != "",
        Dragon.is_epic == False,
    ).first() is not None


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
        UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon.id,
        UserDragon.completed_at == "",
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
    user.epic_unlocked = True
    db.commit()
    if not get_epic_pool(db):
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
        UserDragon.user_id == vk_id,
        UserDragon.dragon_id == user.epic_dragon_id,
        UserDragon.completed_at == "",
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
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or not user.epic_dragon_id:
        return None
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == user.epic_dragon_id
    ).order_by(UserDragon.id.desc()).first()
    if not ud:
        return None
    return db.query(EpicCareState).filter(EpicCareState.user_dragon_id == ud.id).first()


def first_stage(db, dragon_id):
    return (
        db.query(EpicStage)
        .filter(EpicStage.dragon_id == dragon_id)
        .order_by(EpicStage.stage_number, EpicStage.id)
        .first()
    )


def max_stage_number(db, dragon_id):
    stages = db.query(EpicStage).filter(EpicStage.dragon_id == dragon_id).all()
    return max((s.stage_number for s in stages), default=0)


def start_care(db, vk_id):
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return None
    existing = db.query(EpicCareState).filter(EpicCareState.user_dragon_id == ud.id).first()
    if existing:
        return existing
    stage = first_stage(db, ud.dragon_id)
    if not stage:
        return None
    care = EpicCareState(
        user_dragon_id=ud.id, stage_id=stage.id,
        current_action_order=0,
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
    ud = get_epic_user_dragon(db, vk_id)
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
        if ud:
            _record_item_usage(db, vk_id, item.id, ud.id)
    db.commit()


def consume_owned_action_items(db, vk_id, action_id):
    """Consume only the items the user actually owns (respects optional flag)."""
    items = action_items(db, action_id)
    ud = get_epic_user_dragon(db, vk_id)
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
        if ud:
            _record_item_usage(db, vk_id, item.id, ud.id)
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
        nxt = (
            db.query(EpicStage)
            .filter(
                EpicStage.dragon_id == stage.dragon_id,
                EpicStage.stage_number > stage.stage_number,
            )
            .order_by(EpicStage.stage_number, EpicStage.id)
            .first()
        )
        if nxt:
            care.stage_id = nxt.id
            event = {"event": "stage_up", "stage": nxt, "prev_stage": stage}
        else:
            event = {"event": "finale", "stage": stage}

    timeout_action = completed_action or get_current_action(db, care)
    if timeout_action:
        set_care_timeout(db, care, timeout_action)
    else:
        care.next_action_at = None
        care.care_notified = False
    db.commit()
    return event


# ─── Admin care control ───

def admin_advance_care(db, care):
    """Admin: clear any pending sub-action, unlock timeout, then advance one action."""
    care.current_sub_action_id = None
    care.current_step_order = 0
    care.sub_had_penalty = False
    care.next_action_at = None
    care.care_notified = False
    db.commit()
    return advance_care(db, care)


def admin_clear_sub(db, care):
    """Admin: reset a stuck composite sub-action selection."""
    care.current_sub_action_id = None
    care.current_step_order = 0
    care.sub_had_penalty = False
    db.commit()


def admin_goto(db, care, stage_id=None, action_order=None):
    """Admin: jump to a specific stage / action."""
    dragon_id = care_dragon_id(db, care)
    if stage_id is not None:
        stage = db.query(EpicStage).filter(
            EpicStage.id == stage_id, EpicStage.dragon_id == dragon_id
        ).first()
        if not stage:
            return False
        care.stage_id = stage.id
    if action_order is not None:
        actions = get_stage_actions(db, care.stage_id, dragon_id)
        idx = max(0, int(action_order))
        if actions:
            idx = min(idx, len(actions) - 1)
        care.current_action_order = idx
    care.current_sub_action_id = None
    care.current_step_order = 0
    care.sub_had_penalty = False
    care.next_action_at = None
    care.care_notified = False
    db.commit()
    return True


def admin_restart_care(db, care):
    """Admin: reset care to the first stage / first action."""
    dragon_id = care_dragon_id(db, care)
    stage = first_stage(db, dragon_id)
    care.stage_id = stage.id if stage else None
    care.current_action_order = 0
    care.current_sub_action_id = None
    care.current_step_order = 0
    care.sub_had_penalty = False
    care.next_action_at = None
    care.care_notified = False
    db.commit()
    return stage is not None


def care_overview(db, vk_id):
    """Admin: full care state snapshot for the epic dragon of vk_id."""
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return None
    care = db.query(EpicCareState).filter(EpicCareState.user_dragon_id == ud.id).first()
    if not care:
        return None
    dragon_id = ud.dragon_id
    stages = (
        db.query(EpicStage)
        .filter(EpicStage.dragon_id == dragon_id)
        .order_by(EpicStage.stage_number, EpicStage.id)
        .all()
    )
    cur_stage = get_stage(db, care.stage_id)
    actions = get_stage_actions(db, care.stage_id, dragon_id) if care.stage_id else []
    cur_action = get_current_action(db, care)
    sub_action = None
    if care.current_sub_action_id:
        sub_action = get_sub_action(db, care.current_sub_action_id)
    return {
        "dragon_id": dragon_id,
        "stages": [
            {"id": s.id, "stage_number": s.stage_number, "name": s.name}
            for s in stages
        ],
        "stage_id": care.stage_id,
        "stage_name": cur_stage.name if cur_stage else "",
        "stage_number": cur_stage.stage_number if cur_stage else 0,
        "current_action_order": care.current_action_order or 0,
        "actions": [
            {"order_in_cycle": a.order_in_cycle, "action_label": a.action_label, "action_type": getattr(a, "action_type", "simple")}
            for a in actions
        ],
        "current_action_label": cur_action.action_label if cur_action else "",
        "current_sub_action_id": care.current_sub_action_id,
        "current_sub_action_label": sub_action.label if sub_action else "",
        "current_step_order": care.current_step_order or 0,
    }


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
    ud = get_epic_user_dragon(db, vk_id)
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
        if ud:
            _record_item_usage(db, vk_id, item.id, ud.id)
    db.commit()


def restore_sub_items(db, vk_id, sub_id):
    from datetime import datetime
    for item in sub_action_items(db, sub_id):
        if not item.is_consumable:
            continue
        inv = db.query(UserInventory).filter(
            UserInventory.user_id == vk_id,
            UserInventory.item_id == item.id,
        ).first()
        if inv:
            inv.quantity = (inv.quantity or 0) + 1
        else:
            db.add(UserInventory(
                user_id=vk_id, item_id=item.id, quantity=1,
                acquired_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            ))
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


def _record_item_usage(db, vk_id, item_id, user_dragon_id):
    from datetime import datetime
    existing = db.query(UserItemUsage).filter(
        UserItemUsage.user_id == vk_id,
        UserItemUsage.item_id == item_id,
        UserItemUsage.user_dragon_id == user_dragon_id,
    ).first()
    if not existing:
        db.add(UserItemUsage(
            user_id=vk_id,
            item_id=item_id,
            user_dragon_id=user_dragon_id,
            used_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        ))


def get_used_item_ids(db, vk_id):
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return set()
    rows = db.query(UserItemUsage).filter(
        UserItemUsage.user_id == vk_id,
        UserItemUsage.user_dragon_id == ud.id,
    ).all()
    return {r.item_id for r in rows}


def item_in_future_stages(db, vk_id, item_id):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or not user.epic_dragon_id:
        return False
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return False
    care = get_care(db, vk_id)
    current_stage_number = None
    if care and care.stage_id:
        stage = get_stage(db, care.stage_id)
        if stage:
            current_stage_number = stage.stage_number
    future_keys = []
    if current_stage_number is not None:
        future_stages = (
            db.query(EpicStage)
            .filter(
                EpicStage.dragon_id == user.epic_dragon_id,
                EpicStage.stage_number > current_stage_number,
            )
            .all()
        )
        for fs in future_stages:
            future_keys.append(f"epic:{user.epic_dragon_id}:{fs.stage_number}")
    exists = db.query(StageShopItem).filter(
        StageShopItem.item_id == item_id,
        StageShopItem.stage_key.in_(future_keys),
    ).first()
    return exists is not None


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
            image_path=outcome.image_path,
            axis_id=sub_action.character_axis_id if sub_action else None,
        ))
        db.commit()


def outcome_has_content(outcome) -> bool:
    if not outcome:
        return False
    return bool(
        (outcome.moodlet_title or "").strip()
        or (outcome.moodlet_text or "").strip()
        or (outcome.label or "").strip()
        or (outcome.image_path or "").strip()
    )


def resolve_outcome(db, vk_id, care, sub_action):
    if getattr(sub_action, "random_outcome", True):
        polarity = roll_outcome_polarity(db, care)
        outcome = db.query(EpicSubActionOutcome).filter(
            EpicSubActionOutcome.sub_action_id == sub_action.id,
            EpicSubActionOutcome.polarity == polarity,
        ).first()
        if not outcome:
            outcome = db.query(EpicSubActionOutcome).filter(
                EpicSubActionOutcome.sub_action_id == sub_action.id,
            ).first()
    else:
        outcome = (
            db.query(EpicSubActionOutcome)
            .filter(
                EpicSubActionOutcome.sub_action_id == sub_action.id,
                EpicSubActionOutcome.image_path != None,
                EpicSubActionOutcome.image_path != "",
            )
            .order_by(EpicSubActionOutcome.id)
            .first()
        )
        polarity = outcome.polarity if outcome else "positive"

    if outcome and outcome_has_content(outcome):
        _award_outcome_moodlet(db, care.user_dragon_id, polarity, outcome)
    else:
        outcome = None
    from services.character_service import upsert_balance
    if sub_action.character_axis_id:
        delta = 1 if polarity == "positive" else -1
        upsert_balance(db, care.user_dragon_id, sub_action.character_axis_id, delta)
    care.current_sub_action_id = None
    care.current_step_order = 0
    care.sub_had_penalty = False
    db.commit()
    return outcome, polarity


def _award_action_outcome_moodlet(db, user_dragon_id, polarity, outcome, action):
    key = f"action_outcome:{outcome.action_id}:{polarity}"
    existing = db.query(EpicMoodlet).filter(
        EpicMoodlet.user_dragon_id == user_dragon_id,
        EpicMoodlet.key == key,
    ).first()
    if not existing:
        db.add(EpicMoodlet(
            user_dragon_id=user_dragon_id,
            key=key,
            title=outcome.moodlet_title,
            polarity=polarity,
            text=outcome.moodlet_text,
            image_path=outcome.image_path,
            axis_id=action.character_axis_id if action else None,
        ))
        db.commit()


def resolve_action_outcome(db, care, action, had_penalty=False):
    """Resolve the moodlet outcome for a simple (non-composite) action.
    Returns (outcome, polarity) or (None, polarity). Applies character shift."""
    if getattr(action, "random_outcome", True):
        polarity = _roll_action_polarity(db, care, had_penalty)
        outcome = db.query(EpicActionOutcome).filter(
            EpicActionOutcome.action_id == action.id,
            EpicActionOutcome.polarity == polarity,
        ).first()
        if not outcome:
            outcome = db.query(EpicActionOutcome).filter(
                EpicActionOutcome.action_id == action.id,
            ).first()
    else:
        outcome = (
            db.query(EpicActionOutcome)
            .filter(
                EpicActionOutcome.action_id == action.id,
                EpicActionOutcome.image_path != None,
                EpicActionOutcome.image_path != "",
            )
            .order_by(EpicActionOutcome.id)
            .first()
        )
        polarity = outcome.polarity if outcome else "positive"

    if outcome and outcome_has_content(outcome):
        _award_action_outcome_moodlet(db, care.user_dragon_id, polarity, outcome, action)
    else:
        outcome = None
    from services.character_service import upsert_balance
    if getattr(action, "character_axis_id", None):
        delta = 1 if polarity == "positive" else -1
        upsert_balance(db, care.user_dragon_id, action.character_axis_id, delta)
    db.commit()
    return outcome, polarity


def _roll_action_polarity(db, care, had_penalty=False):
    balances = db.query(CharacterBalance).filter(
        CharacterBalance.user_dragon_id == care.user_dragon_id
    ).all()
    pos = sum(max(b.score or 0, 0) for b in balances)
    neg = sum(max(-(b.score or 0), 0) for b in balances)
    char_component = pos / (pos + neg) if pos + neg > 0 else 0.5
    penalty_mult = 0.5 if had_penalty else 1.0
    chance = max(0.05, min(0.95, char_component * penalty_mult))
    return "positive" if random.random() < chance else "negative"


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


# ─── Incubator ───

def get_incubator_epics(db, vk_id):
    """Return all epic dragons with status/cost for the incubator view."""
    pool = get_epic_pool(db)
    user = db.query(User).filter(User.vk_id == vk_id).first()
    active_id = user.epic_dragon_id if user else None
    result = []
    for d in pool:
        uds = db.query(UserDragon).filter(
            UserDragon.user_id == vk_id, UserDragon.dragon_id == d.id
        ).all()
        growing = [u for u in uds if not u.completed_at]
        completed = [u for u in uds if u.completed_at]
        if growing:
            status = "growing"
            ud = growing[0]
        elif completed:
            status = "completed"
            ud = completed[0]
        else:
            status = "available"
            ud = None
        egg_done = db.query(UserProgress).filter(
            UserProgress.user_id == vk_id,
            UserProgress.dragon_id == d.id,
            UserProgress.step_number > 0,
            UserProgress.completed == True,
        ).count()
        egg_total_val = d.steps_count or 0
        egg_hatched = egg_total_val > 0 and egg_done >= egg_total_val
        has_care = False
        if ud:
            has_care = db.query(EpicCareState).filter(
                EpicCareState.user_dragon_id == ud.id
            ).first() is not None
        is_active = active_id == d.id
        cost = d.epic_cost_stitches or 0
        result.append({
            "dragon": d,
            "status": status,
            "cost": cost,
            "is_active": is_active,
            "egg_hatched": egg_hatched,
        })
    return result


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
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        return None, False
    user.epic_dragon_id = target_id
    user.epic_unlocked = True
    db.add(UserDragon(user_id=vk_id, dragon_id=target_id, completed_at=""))
    db.commit()
    return db.query(Dragon).filter(Dragon.id == target_id).first(), had_others


def purchase_epic_egg(db, vk_id, dragon_id):
    """Purchase an epic dragon egg. Always creates a new slot — never resets a completed one."""
    from datetime import datetime
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        return False, "Пользователь не найден.", None
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id, Dragon.is_epic == True).first()
    if not dragon:
        return False, "Эпический дракон не найден.", None
    cost = dragon.epic_cost_stitches or 0
    if cost <= 0:
        return False, "Этот эпический дракон недоступен для покупки.", None
    uds = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id
    ).all()
    growing = [u for u in uds if not u.completed_at]
    if growing:
        return False, "Этот эпический дракон уже растёт.", None
    balance = user.stitches_balance or 0
    if balance < cost:
        return False, f"Недостаточно крестиков. Нужно {cost}, у вас {balance}.", None
    user.stitches_balance = balance - cost
    user.epic_dragon_id = dragon_id
    user.epic_unlocked = True
    db.add(UserDragon(user_id=vk_id, dragon_id=dragon_id, completed_at=""))
    db.commit()
    return True, f"Яйцо «{dragon.egg_type or dragon.name}» куплено за {cost} ✚!", dragon


def all_user_epics(db, vk_id):
    """Return all ACTIVE (non-completed) epic dragons for the user."""
    return (
        db.query(Dragon)
        .join(UserDragon, UserDragon.dragon_id == Dragon.id)
        .filter(
            UserDragon.user_id == vk_id,
            Dragon.is_epic == True,
            UserDragon.completed_at == "",
        )
        .order_by(UserDragon.id)
        .all()
    )

