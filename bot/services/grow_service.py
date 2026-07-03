"""Growing logic: step definitions, progress tracking, completion."""

from datetime import datetime, timedelta


def get_dragon_step(db, dragon_id: int, step_number: int):
    from models import DragonStep
    return db.query(DragonStep).filter(
        DragonStep.dragon_id == dragon_id,
        DragonStep.step_number == step_number,
    ).first()


def get_total_steps(db, dragon_id: int) -> int:
    from models import Dragon
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    return dragon.steps_count if dragon else 0


def get_step_timeout(db, dragon_id: int, step_number: int) -> tuple[int, int]:
    step = get_dragon_step(db, dragon_id, step_number)
    if not step:
        return (0, 0)
    return (step.timeout_hours or 0, step.timeout_minutes or 0)


def get_timeout_remaining(db, vk_id: int, dragon_id: int):
    from models import UserDragon
    from datetime import timezone
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id
    ).first()
    if not ud or not ud.next_step_available_at:
        return None
    try:
        available = datetime.fromisoformat(ud.next_step_available_at)
        now = datetime.now().astimezone() if available.tzinfo else datetime.now()
        remaining = available - now
        if remaining.total_seconds() <= 0:
            return None
        return remaining
    except (ValueError, TypeError):
        return None


def set_step_timeout(db, vk_id: int, dragon_id: int, step_number: int):
    hours, minutes = get_step_timeout(db, dragon_id, step_number)
    total_minutes = hours * 60 + minutes
    if total_minutes <= 0:
        return
    from models import UserDragon
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id
    ).first()
    if ud:
        available = datetime.now() + timedelta(minutes=total_minutes)
        ud.next_step_available_at = available.strftime("%Y-%m-%dT%H:%M:%S")
        ud.timeout_notified = False
        db.commit()


def clear_step_timeout(db, vk_id: int, dragon_id: int):
    from models import UserDragon
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id
    ).first()
    if ud and ud.next_step_available_at:
        ud.next_step_available_at = None
        db.commit()


def complete_step(db, vk_id: int, dragon_id: int, step_number: int, photo_before_id: str = "", photo_after_id: str = ""):
    from models import UserProgress
    existing = db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == dragon_id,
        UserProgress.step_number == step_number,
    ).first()
    if existing:
        existing.completed = True
        existing.completed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if photo_before_id:
            existing.photo_before_id = photo_before_id
        if photo_after_id:
            existing.photo_after_id = photo_after_id
    else:
        up = UserProgress(
            user_id=vk_id,
            dragon_id=dragon_id,
            step_number=step_number,
            completed=True,
            completed_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            photo_before_id=photo_before_id,
            photo_after_id=photo_after_id,
        )
        db.add(up)
    db.commit()


def complete_dragon(db, vk_id: int, dragon_id: int):
    from models import UserDragon
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id
    ).first()
    if ud:
        ud.completed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        ud.next_step_available_at = None
        ud.timeout_notified = False
        db.commit()
