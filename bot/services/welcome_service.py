import sys
import os
import random

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "api"))


def ensure_donor_welcome_pin(db, vk_id: int) -> bool:
    from services.payment_service import is_donor

    if not is_donor(vk_id, db):
        return False

    from models import UserRewardPin
    existing = db.query(UserRewardPin).filter(
        UserRewardPin.user_id == vk_id,
        UserRewardPin.config_id.is_(None),
    ).first()
    if existing:
        return False

    from models import Dragon, UserDragon, DragonReservation
    from datetime import datetime

    owned_ids = set(
        row[0] for row in db.query(UserDragon.dragon_id).filter(
            UserDragon.user_id == vk_id,
        ).all()
    )
    own_reserved_ids = set(
        row[0] for row in db.query(DragonReservation.dragon_id).filter(
            DragonReservation.vk_user_id == vk_id,
            DragonReservation.is_activated == False,
        ).all()
    )
    excluded = owned_ids | own_reserved_ids

    available = db.query(Dragon).filter(
        Dragon.is_active == True,
        Dragon.is_epic == False,
        Dragon.pin_code.isnot(None),
        Dragon.pin_code != "",
    ).all()
    available = [d for d in available if d.id not in excluded]
    if not available:
        return False

    dragon = random.choice(available)
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    reservation = DragonReservation(
        vk_url=f"https://vk.ru/id{vk_id}",
        vk_user_id=vk_id,
        dragon_id=dragon.id,
        is_activated=False,
        notes="Welcome-PIN для дона",
        created_at=now_str,
        updated_at=now_str,
    )
    db.add(reservation)

    pin_record = UserRewardPin(
        user_id=vk_id,
        dragon_id=dragon.id,
        pin_code=dragon.pin_code or "",
        config_id=None,
        issued_at=now_str,
        activated=False,
        notified=False,
    )
    db.add(pin_record)

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
    return True
