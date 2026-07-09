from models import Dragon, User, UserDragon, DonorCache, DragonSet, PaymentOrder, PricingConfig
from services.payment_service import (
    get_base_price, set_base_price, is_donor, calc_set_price,
    count_available, select_dragons,
)


def _dragon(db, name, family_id=None, pin="P0001", active=True):
    d = Dragon(name=name, egg_type="egg", rarity=1, steps_count=1,
               pin_code=pin, family_id=family_id, is_active=active)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def test_get_base_price_default(db):
    assert get_base_price(db) == 10000


def test_set_and_get_base_price(db):
    set_base_price(db, 20000)
    assert get_base_price(db) == 20000


def test_is_donor(db):
    db.add(DonorCache(vk_id=555, is_don=True))
    db.add(DonorCache(vk_id=777, is_don=False))
    db.commit()
    assert is_donor(555, db) is True
    assert is_donor(777, db) is False
    assert is_donor(999, db) is False


def test_calc_set_price_normal(db):
    s = DragonSet(name="5", quantity=5, discount_percent=5, donor_discount_percent=15)
    total, per_pin = calc_set_price(s, False, db)
    assert total == 47500
    assert per_pin == 9500


def test_calc_set_price_donor(db):
    s = DragonSet(name="5", quantity=5, discount_percent=5, donor_discount_percent=15)
    total, per_pin = calc_set_price(s, True, db)
    assert total == 42500
    assert per_pin == 8500


def test_count_available_excludes_owned(db):
    d1 = _dragon(db, "A", pin="A0001")
    _dragon(db, "B", pin="B0001")
    db.add(UserDragon(user_id=1, dragon_id=d1.id))
    db.commit()
    assert count_available(1, db) == 1


def test_count_available_excludes_purchased(db):
    d1 = _dragon(db, "A", pin="A0002")
    _dragon(db, "B", pin="B0002")
    db.add(PaymentOrder(vk_id=1, set_id=None, status="success", dragon_ids=f"[{d1.id}]"))
    db.commit()
    assert count_available(1, db) == 1


def test_count_available_excludes_inactive(db):
    _dragon(db, "A", pin="A0003")
    _dragon(db, "B", pin="B0003", active=False)
    assert count_available(1, db) == 1


def test_select_dragons_prefers_different_families(db):
    _dragon(db, "A1", family_id=1, pin="A0004")
    _dragon(db, "A2", family_id=1, pin="A0005")
    _dragon(db, "B1", family_id=2, pin="B0004")
    _dragon(db, "B2", family_id=2, pin="B0005")
    picked = select_dragons(1, 2, db)
    fams = {d.family_id for d in picked}
    assert len(picked) == 2
    assert fams == {1, 2}


def test_select_dragons_fills_from_same_family(db):
    _dragon(db, "A1", family_id=1, pin="A0006")
    _dragon(db, "A2", family_id=1, pin="A0007")
    _dragon(db, "A3", family_id=1, pin="A0008")
    _dragon(db, "B1", family_id=2, pin="B0006")
    picked = select_dragons(1, 3, db)
    assert len(picked) == 3


def test_select_dragons_fewer_available(db):
    _dragon(db, "A", family_id=1, pin="A0009")
    _dragon(db, "B", family_id=2, pin="B0009")
    picked = select_dragons(1, 5, db)
    assert len(picked) == 2
