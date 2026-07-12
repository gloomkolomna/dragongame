from models import (
    User, UserDragon, ShopItem, StageShopItem, UserInventory,
    EpicStage, EpicCareState,
)
from services import shop_service


def _epic_egg_user(db, vk_id=100, epic_dragon_id=50, balance=1000):
    db.add(User(vk_id=vk_id, stitches_balance=balance, epic_dragon_id=epic_dragon_id))
    db.add(UserDragon(user_id=vk_id, dragon_id=epic_dragon_id, completed_at=""))
    db.commit()


def _item(db, name="Food", cost=100, active=True):
    it = ShopItem(name=name, cost_stitches=cost, is_active=active)
    db.add(it)
    db.flush()
    return it


def test_stage_key_none_without_epic(db):
    db.add(User(vk_id=1))
    db.commit()
    assert shop_service.get_current_stage_key(db, 1) is None


def test_stage_key_egg(db):
    _epic_egg_user(db)
    assert shop_service.get_current_stage_key(db, 100) == "epic:50:egg"


def test_stage_key_care_stage(db):
    _epic_egg_user(db)
    stage = EpicStage(dragon_id=50, stage_number=2, name="S2")
    db.add(stage)
    db.flush()
    ud = db.query(UserDragon).filter(UserDragon.user_id == 100).first()
    db.add(EpicCareState(user_dragon_id=ud.id, stage_id=stage.id))
    db.commit()
    assert shop_service.get_current_stage_key(db, 100) == "epic:50:2"


def test_get_stage_items_filters_active(db):
    _epic_egg_user(db)
    a = _item(db, name="A", active=True)
    b = _item(db, name="B", active=False)
    db.add(StageShopItem(stage_key="epic:50:egg", item_id=a.id))
    db.add(StageShopItem(stage_key="epic:50:egg", item_id=b.id))
    db.commit()
    items = shop_service.get_stage_items(db, "epic:50:egg")
    assert [i.name for i in items] == ["A"]


def test_purchase_ok_and_repeat(db):
    _epic_egg_user(db, balance=1000)
    it = _item(db, cost=300)
    db.add(StageShopItem(stage_key="epic:50:egg", item_id=it.id))
    db.commit()

    res = shop_service.purchase(db, 100, it.id)
    assert res["status"] == "ok"
    assert res["balance"] == 700
    assert shop_service.owns_item(db, 100, it.id)

    res2 = shop_service.purchase(db, 100, it.id)
    assert res2["status"] == "already"
    u = db.query(User).filter(User.vk_id == 100).first()
    assert u.stitches_balance == 700


def test_purchase_insufficient(db):
    _epic_egg_user(db, vk_id=101, epic_dragon_id=50, balance=50)
    it = _item(db, cost=300)
    db.add(StageShopItem(stage_key="epic:50:egg", item_id=it.id))
    db.commit()
    res = shop_service.purchase(db, 101, it.id)
    assert res["status"] == "insufficient"
    u = db.query(User).filter(User.vk_id == 101).first()
    assert u.stitches_balance == 50


def test_purchase_not_on_stage(db):
    _epic_egg_user(db, vk_id=102)
    it = _item(db, cost=100)
    db.commit()
    res = shop_service.purchase(db, 102, it.id)
    assert res["status"] == "not_on_stage"


def test_api_shop_and_inventory(client, db):
    _epic_egg_user(db, vk_id=103)
    it = _item(db, name="Bottle", cost=100)
    db.add(StageShopItem(stage_key="epic:50:egg", item_id=it.id))
    db.add(UserInventory(user_id=103, item_id=it.id, quantity=1))
    db.commit()

    shop = client.get("/api/collection/103/shop").json()
    assert shop["stage_key"] == "epic:50:egg"
    assert len(shop["items"]) == 1
    assert shop["items"][0]["owned"] is True

    inv = client.get("/api/collection/103/inventory").json()
    assert inv[0]["name"] == "Bottle"
    assert inv[0]["quantity"] == 1


def test_api_shop_empty_without_epic(client, db):
    db.add(User(vk_id=104))
    db.commit()
    shop = client.get("/api/collection/104/shop").json()
    assert shop["stage_key"] is None
    assert shop["items"] == []


def test_api_no_purchase_endpoint(client):
    r = client.post("/api/collection/103/shop")
    assert r.status_code in (404, 405)
