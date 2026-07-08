"""Epic dragon service — spawn, naming, egg/hatch, care state. Pure DB, no VK."""

import random
from datetime import datetime, timedelta
from models import (
    User, Dragon, UserDragon, UserProgress, DragonStep,
    EpicStage, EpicStageAction, EpicActionItem, EpicCareState,
    UserInventory, EpicMoodlet, ShopItem,
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


def get_stage_actions(db, stage_id):
    return (
        db.query(EpicStageAction)
        .filter(EpicStageAction.stage_id == stage_id)
        .order_by(EpicStageAction.order_in_cycle, EpicStageAction.id)
        .all()
    )


def get_current_action(db, care):
    if not care or not care.stage_id:
        return None
    actions = get_stage_actions(db, care.stage_id)
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


def missing_action_items(db, vk_id, action_id):
    owned = {
        inv.item_id for inv in db.query(UserInventory).filter(UserInventory.user_id == vk_id).all()
    }
    return [it for it in action_items(db, action_id) if it.id not in owned]


def set_care_timeout(db, care, stage):
    minutes = (stage.care_timeout_hours or 0) * 60 + (stage.care_timeout_minutes or 0)
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
    actions = get_stage_actions(db, care.stage_id)
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

    set_care_timeout(db, care, get_stage(db, care.stage_id) or stage)
    db.commit()
    return event


# ─── Character + finale + restart ───

def character_effects(db, vk_id):
    rows = db.query(UserInventory).filter(UserInventory.user_id == vk_id).all()
    effects = []
    for inv in rows:
        item = db.query(ShopItem).filter(ShopItem.id == inv.item_id).first()
        if item and item.character_effect:
            eff = item.character_effect.strip()
            if eff and eff not in effects:
                effects.append(eff)
    return effects


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

