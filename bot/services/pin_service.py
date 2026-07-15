"""PIN validation and activation."""

from datetime import datetime


def _update_reservation_on_activation(db, vk_id: int, dragon_id: int):
    from models import DragonReservation
    reservation = db.query(DragonReservation).filter(
        DragonReservation.dragon_id == dragon_id,
        DragonReservation.is_activated == False,
    ).first()
    if reservation:
        reservation.is_activated = True
        reservation.activated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if not reservation.vk_user_id:
            reservation.vk_user_id = vk_id
        if not reservation.vk_name:
            try:
                import config
                if config.VK_GROUP_TOKEN:
                    import vk_api
                    vk = vk_api.VkApi(token=config.VK_GROUP_TOKEN, api_version="5.199").get_api()
                    users = vk.users.get(user_ids=str(vk_id), fields="first_name,last_name")
                    if users:
                        u = users[0]
                        reservation.vk_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
            except Exception:
                pass
        db.commit()


def validate_pin_code(db, code: str):
    from models import Dragon
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
    _update_reservation_on_activation(db, vk_id, dragon.id)
    return True
