"""Growing logic: step definitions, progress tracking, completion."""

import traceback
from datetime import datetime, timedelta

RARITY_NAMES = {1: "обычный", 2: "редкий", 3: "легендарный"}
MAX_RARITY = 3


def rarity_name(rarity: int) -> str:
    return RARITY_NAMES.get(rarity, "легендарный")


def log_to_db(source: str, error_type: str, message: str, traceback_text: str = "", user_id: int = None, db=None):
    try:
        if db is None:
            from db import SessionLocal
            db = SessionLocal()
            _own = True
        else:
            _own = False
        from models import ErrorLog
        db.add(ErrorLog(
            source=source,
            error_type=error_type,
            message=message,
            traceback_text=traceback_text,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
        ))
        db.commit()
        if _own:
            db.close()
    except Exception:
        traceback.print_exc()


def rarity_stars(rarity: int) -> str:
    return "⭐" * min(rarity, MAX_RARITY)


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


def award_treasure(db, vk_id: int, dragon_id: int):
    from models import Dragon, Treasure, UserTreasure
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon or dragon.rarity != 2:
        return None
    treasure = db.query(Treasure).filter(
        Treasure.dragon_id == dragon_id, Treasure.is_active == True
    ).first()
    if not treasure:
        return None
    existing = db.query(UserTreasure).filter(
        UserTreasure.user_id == vk_id, UserTreasure.treasure_id == treasure.id
    ).first()
    if existing:
        return None
    db.add(UserTreasure(user_id=vk_id, treasure_id=treasure.id))
    db.commit()
    return treasure


def award_family_treasures(db, vk_id: int):
    from models import Dragon, Family, Treasure, UserTreasure, UserDragon

    user_dragon_ids = {
        ud.dragon_id for ud in db.query(UserDragon).filter(
            UserDragon.user_id == vk_id,
            UserDragon.completed_at.isnot(None),
        ).all()
    }
    if not user_dragon_ids:
        return []

    families = {
        f.id: f for f in db.query(Family).all()
    }
    dragons = db.query(Dragon).filter(Dragon.id.in_(user_dragon_ids)).all()
    family_dragons: dict[int, set] = {}
    for d in dragons:
        f = families.get(d.family_id)
        if f:
            family_dragons.setdefault(f.id, set()).add(d.id)

    awarded = []
    for fid, completed_ids in family_dragons.items():
        all_in_family = {d.id for d in db.query(Dragon).filter(
            Dragon.family_id == fid, Dragon.is_active == True
        ).all()}
        if not all_in_family:
            continue
        if not all_in_family.issubset(completed_ids):
            continue
        treasure = db.query(Treasure).filter(
            Treasure.family_id == fid, Treasure.is_active == True
        ).first()
        if not treasure:
            continue
        existing = db.query(UserTreasure).filter(
            UserTreasure.user_id == vk_id,
            UserTreasure.treasure_id == treasure.id,
        ).first()
        if existing:
            continue
        db.add(UserTreasure(user_id=vk_id, treasure_id=treasure.id))
        awarded.append(treasure)

    if awarded:
        db.commit()
    return awarded


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
    treasure = award_treasure(db, vk_id, dragon_id)
    family_treasures = award_family_treasures(db, vk_id)
    return treasure, family_treasures


def get_anti_cheat_multiplier() -> int:
    try:
        import config
        return max(2, int(config.ANTI_CHEAT_MULTIPLIER or 5))
    except Exception:
        return 5


def credit_stitches(db, vk_id: int, amount: int) -> int:
    from models import User
    if amount <= 0:
        user = db.query(User).filter(User.vk_id == vk_id).first()
        return user.stitches_balance if user else 0
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        return 0
    user.stitches_balance = (user.stitches_balance or 0) + amount
    db.commit()
    return user.stitches_balance


def is_suspicious(declared: int, required: int) -> bool:
    if required <= 0:
        return False
    return declared > required * get_anti_cheat_multiplier()


def create_suspicious_report(db, vk_id, dragon_id, step_number, declared, required, mode,
                             photo_before_id="", photo_after_id="", raw_message=""):
    from models import SuspiciousReport
    report = SuspiciousReport(
        user_id=vk_id,
        dragon_id=dragon_id,
        step_number=step_number,
        declared_crosses=declared,
        normal_crosses=required,
        mode=mode,
        raw_message=raw_message or "",
        photo_before_id=photo_before_id,
        photo_after_id=photo_after_id,
        status="pending",
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(report)
    db.commit()
    return report


def notify_admin(message: str):
    try:
        import config
        import random
        admin_id = getattr(config, "ADMIN_VK_ID", 0)
        if not admin_id or not config.VK_GROUP_TOKEN:
            return
        import vk_api
        vk = vk_api.VkApi(token=config.VK_GROUP_TOKEN, api_version="5.199").get_api()
        vk.messages.send(
            user_id=admin_id,
            message=message,
            random_id=random.randint(1, 2**31 - 1),
        )
    except Exception as e:
        log_to_db(
            source="bot",
            error_type="NOTIFY_ADMIN",
            message=f"notify_admin failed: {e} | original: {message[:200]}",
            traceback_text=traceback.format_exc(),
        )
