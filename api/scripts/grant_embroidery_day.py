import argparse
import random
import sys
from datetime import datetime
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from db import SessionLocal
from models import Dragon, DragonReservation, User, UserRewardPin
from services.external_rewards import available_reservation_dragons

SOURCE = "embroidery_day_2026"
REWARD_PREFIX = "embroidery_day:2026"
NOTES = "Подарок ко Дню вышивальщицы 2026"


def _reward_id(vk_id):
    return f"{REWARD_PREFIX}:{vk_id}"


def grant_random_dragon(db, user, apply=False):
    external_reward_id = _reward_id(user.vk_id)
    existing = db.query(DragonReservation).filter(
        DragonReservation.external_reward_id == external_reward_id,
    ).first()
    if existing:
        dragon = db.query(Dragon).filter(Dragon.id == existing.dragon_id).first()
        return "existing", dragon

    pool = available_reservation_dragons(db, user.vk_id)
    if not pool:
        return "unavailable", None

    dragon = random.choice(pool)
    if not apply:
        return "planned", dragon

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    db.add(DragonReservation(
        vk_url=f"https://vk.ru/id{user.vk_id}",
        vk_user_id=user.vk_id,
        dragon_id=dragon.id,
        is_activated=False,
        source=SOURCE,
        external_reward_id=external_reward_id,
        notes=NOTES,
        created_at=now,
        updated_at=now,
    ))
    db.add(UserRewardPin(
        user_id=user.vk_id,
        dragon_id=dragon.id,
        pin_code=dragon.pin_code or "",
        source=SOURCE,
        external_reward_id=external_reward_id,
        issued_at=now,
        activated=False,
        notified=False,
    ))
    db.commit()
    return "created", dragon


def run(db, apply=False):
    users = db.query(User).order_by(User.vk_id).all()
    counts = {
        "created": 0,
        "planned": 0,
        "existing": 0,
        "unavailable": 0,
        "failed": 0,
    }
    labels = {
        "created": "бронь создана",
        "planned": "бронь запланирована",
        "existing": "подарок уже выдан",
    }

    for user in users:
        try:
            status, dragon = grant_random_dragon(db, user, apply=apply)
        except Exception as exc:
            db.rollback()
            status = "failed"
            print(f"id{user.vk_id}: ошибка — {exc}")
        else:
            if status == "unavailable":
                print(f"id{user.vk_id}: нет доступных драконов")
            else:
                dragon_name = dragon.name if dragon else "дракон не найден"
                print(f"id{user.vk_id}: {labels[status]} — {dragon_name}")
        counts[status] += 1

    print(
        f"\nВсего пользователей: {len(users)}; "
        f"создано: {counts['created']}; "
        f"запланировано: {counts['planned']}; "
        f"уже выдано: {counts['existing']}; "
        f"без доступных драконов: {counts['unavailable']}; "
        f"ошибок: {counts['failed']}."
    )
    if not apply:
        print("База данных не изменена. Для выдачи подарков запустите скрипт с --apply.")
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Резервирует каждому пользователю случайного дракона ко Дню вышивальщицы 2026.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Сохранить брони и наградные PIN-коды в базе данных.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        counts = run(db, apply=args.apply)
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
