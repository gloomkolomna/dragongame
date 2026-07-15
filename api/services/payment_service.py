import json
import random
from datetime import datetime


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def get_base_price(db) -> int:
    from models import PricingConfig
    cfg = db.query(PricingConfig).filter(PricingConfig.id == 1).first()
    if not cfg:
        return 10000
    return cfg.base_price_per_dragon


def set_base_price(db, price_kop: int) -> int:
    from models import PricingConfig
    cfg = db.query(PricingConfig).filter(PricingConfig.id == 1).first()
    if not cfg:
        cfg = PricingConfig(id=1, base_price_per_dragon=price_kop, updated_at=_now())
        db.add(cfg)
    else:
        cfg.base_price_per_dragon = price_kop
        cfg.updated_at = _now()
    db.commit()
    return cfg.base_price_per_dragon


def is_donor(vk_id: int, db) -> bool:
    from models import DonorCache
    row = db.query(DonorCache).filter(DonorCache.vk_id == vk_id).first()
    return bool(row and row.is_don)


def get_effective_price(vk_id: int, db) -> int:
    from models import User
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if user and user.custom_price_per_dragon is not None:
        return user.custom_price_per_dragon
    return get_base_price(db)


def calc_set_price(dset, donor: bool, vk_id: int, db) -> tuple[int, int]:
    base = get_effective_price(vk_id, db)
    discount = dset.donor_discount_percent if donor else dset.discount_percent
    total = dset.quantity * base * (100 - discount) // 100
    price_per_pin = base * (100 - discount) // 100
    return total, price_per_pin


def _reserved_dragon_ids(vk_id: int, db) -> set:
    from models import PaymentOrder
    ids = set()
    orders = db.query(PaymentOrder).filter(
        PaymentOrder.vk_id == vk_id,
        PaymentOrder.status == "success",
    ).all()
    for o in orders:
        try:
            ids.update(json.loads(o.dragon_ids or "[]"))
        except Exception:
            pass
    return ids


def _available_dragons(vk_id: int, db) -> list:
    from models import Dragon, UserDragon, DragonReservation
    owned = {
        r[0] for r in db.query(UserDragon.dragon_id).filter(UserDragon.user_id == vk_id).all()
    }
    reserved = {
        r[0] for r in db.query(DragonReservation.dragon_id).filter(
            DragonReservation.is_activated == False,
            ((DragonReservation.vk_user_id == vk_id) | (DragonReservation.vk_user_id == None)),
        ).all()
    }
    exclude = owned | _reserved_dragon_ids(vk_id, db) | reserved
    dragons = db.query(Dragon).filter(Dragon.is_active == True, Dragon.is_epic == False).all()
    return [d for d in dragons if d.id not in exclude]


def count_available(vk_id: int, db) -> int:
    return len(_available_dragons(vk_id, db))


def select_dragons(vk_id: int, count: int, db) -> list:
    available = _available_dragons(vk_id, db)
    if len(available) <= count:
        random.shuffle(available)
        return available

    groups: dict = {}
    for d in available:
        groups.setdefault(d.family_id or 0, []).append(d)
    for g in groups.values():
        random.shuffle(g)

    pool = []
    remaining = []
    for g in groups.values():
        pool.append(g[0])
        remaining.extend(g[1:])
    random.shuffle(pool)

    if len(pool) >= count:
        return pool[:count]

    random.shuffle(remaining)
    pool.extend(remaining[: count - len(pool)])
    return pool
