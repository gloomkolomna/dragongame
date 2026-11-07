import random
from datetime import datetime

from sqlalchemy.exc import IntegrityError


class ExternalRewardError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def available_reservation_dragons(db, vk_user_id):
    from models import Dragon, DragonReservation, UserDragon

    excluded = set()
    if vk_user_id:
        excluded = {
            row[0]
            for row in db.query(DragonReservation.dragon_id).filter(
                DragonReservation.vk_user_id == vk_user_id,
                DragonReservation.revoked_at.is_(None),
            ).all()
        }
        excluded |= {
            row[0]
            for row in db.query(UserDragon.dragon_id).filter(UserDragon.user_id == vk_user_id).all()
        }
    query = db.query(Dragon).filter(
        Dragon.is_active == True,
        Dragon.is_epic == False,
        Dragon.pin_code.isnot(None),
        Dragon.pin_code != "",
    )
    if excluded:
        query = query.filter(~Dragon.id.in_(excluded))
    return query.all()


def _reward_dict(reservation, user_registered):
    return {
        "reservation_id": reservation.id,
        "dragon_id": reservation.dragon_id,
        "user_registered": user_registered,
        "status": "revoked" if reservation.revoked_at else "activated" if reservation.is_activated else "reserved",
    }


def grant_random_egg(db, vk_id: int, external_reward_id: str):
    from models import DragonReservation, User, UserRewardPin

    existing = db.query(DragonReservation).filter(
        DragonReservation.external_reward_id == external_reward_id,
    ).first()
    if existing:
        user = db.query(User).filter(User.vk_id == vk_id).first()
        return _reward_dict(existing, user is not None)

    pool = available_reservation_dragons(db, vk_id)
    if not pool:
        raise ExternalRewardError(409, "Нет доступных яиц для выдачи")

    dragon = random.choice(pool)
    user = db.query(User).filter(User.vk_id == vk_id).first()
    now = _now()
    reservation = DragonReservation(
        vk_url=f"https://vk.ru/id{vk_id}",
        vk_user_id=vk_id,
        dragon_id=dragon.id,
        is_activated=False,
        source="holidays",
        external_reward_id=external_reward_id,
        notes="Награда из «Улицы праздников»",
        created_at=now,
        updated_at=now,
    )
    db.add(reservation)
    try:
        db.flush()
        if user:
            db.add(UserRewardPin(
                user_id=vk_id,
                dragon_id=dragon.id,
                pin_code=dragon.pin_code or "",
                source="holidays",
                external_reward_id=external_reward_id,
                issued_at=now,
                activated=False,
                notified=False,
            ))
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(DragonReservation).filter(
            DragonReservation.external_reward_id == external_reward_id,
        ).first()
        if existing:
            return _reward_dict(existing, user is not None)
        raise
    db.refresh(reservation)
    return _reward_dict(reservation, user is not None)


def ensure_external_reward_pins(db, vk_id: int):
    from models import Dragon, DragonReservation, UserRewardPin

    reservations = db.query(DragonReservation).filter(
        DragonReservation.vk_user_id == vk_id,
        DragonReservation.source == "holidays",
        DragonReservation.is_activated == False,
        DragonReservation.revoked_at.is_(None),
    ).all()
    if not reservations:
        return 0
    existing = {
        row[0]
        for row in db.query(UserRewardPin.external_reward_id).filter(
            UserRewardPin.user_id == vk_id,
            UserRewardPin.external_reward_id.isnot(None),
        ).all()
    }
    created = 0
    now = _now()
    for reservation in reservations:
        if reservation.external_reward_id in existing:
            continue
        dragon = db.query(Dragon).filter(Dragon.id == reservation.dragon_id).first()
        if dragon is None:
            continue
        db.add(UserRewardPin(
            user_id=vk_id,
            dragon_id=dragon.id,
            pin_code=dragon.pin_code or "",
            source="holidays",
            external_reward_id=reservation.external_reward_id,
            issued_at=now,
            activated=False,
            notified=False,
        ))
        created += 1
    if created:
        db.commit()
    return created


def revoke_egg(db, external_reward_id: str):
    from models import DragonReservation, UserRewardPin

    reservation = db.query(DragonReservation).filter(
        DragonReservation.external_reward_id == external_reward_id,
    ).first()
    if reservation is None:
        raise ExternalRewardError(404, "Бронь награды не найдена")
    if reservation.is_activated:
        raise ExternalRewardError(409, "Яйцо уже активировано — отозвать нельзя")
    if reservation.revoked_at:
        return {"ok": True, "status": "revoked"}
    reservation.revoked_at = _now()
    pins = db.query(UserRewardPin).filter(
        UserRewardPin.external_reward_id == external_reward_id,
        UserRewardPin.activated == False,
    ).all()
    for pin in pins:
        db.delete(pin)
    db.commit()
    return {"ok": True, "status": "revoked"}
