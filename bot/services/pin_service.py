"""PIN validation and activation."""

from datetime import datetime


def validate_pin_code(db, code: str):
    from models import Dragon, UserDragon
    dragon = db.query(Dragon).filter(Dragon.pin_code == code, Dragon.is_active == True).first()
    if not dragon:
        return None
    return dragon


def activate_pin(db, vk_id: int, dragon):
    from models import UserDragon

    existing = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon.id
    ).first()
    if existing:
        return False

    ud = UserDragon(
        user_id=vk_id,
        dragon_id=dragon.id,
        completed_at="",
    )
    db.add(ud)
    db.commit()
    return True
