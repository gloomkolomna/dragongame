from models import User, UserDragon, ShopItem, StageShopItem
from bot.handlers.shop import handle_shop_command, handle_buy


def _epic_egg_user(db, vk_id=1, balance=1000):
    db.add(User(vk_id=vk_id, state="idle", stitches_balance=balance, epic_dragon_id=50))
    db.add(UserDragon(user_id=vk_id, dragon_id=50, completed_at=""))
    db.commit()
    return db.query(User).filter(User.vk_id == vk_id).first()


def _bind_item(db, name="Food", cost=100):
    it = ShopItem(name=name, cost_stitches=cost, is_active=True)
    db.add(it)
    db.flush()
    db.add(StageShopItem(stage_key="epic:egg", item_id=it.id))
    db.commit()
    return it


def test_shop_no_epic(db):
    db.add(User(vk_id=2, state="idle"))
    db.commit()
    u = db.query(User).filter(User.vk_id == 2).first()
    msgs = []
    handle_shop_command(u, db, lambda m, **k: msgs.append(m))
    assert "эпическ" in msgs[0].lower()


def test_shop_lists_items(db):
    u = _epic_egg_user(db)
    _bind_item(db, name="Food")
    msgs, kbs = [], []

    def send(m, keyboard=None, **k):
        msgs.append(m)
        kbs.append(keyboard)

    handle_shop_command(u, db, send)
    assert "Food" in msgs[0]
    assert kbs[0] is not None


def test_buy_ok_deducts(db):
    u = _epic_egg_user(db, balance=500)
    it = _bind_item(db, cost=100)
    msgs = []
    handle_buy(u, it.id, db, lambda m, **k: msgs.append(m))
    assert any("Куплено" in m for m in msgs)
    db.refresh(u)
    assert u.stitches_balance == 400


def test_buy_insufficient(db):
    u = _epic_egg_user(db, balance=50)
    it = _bind_item(db, cost=100)
    msgs = []
    handle_buy(u, it.id, db, lambda m, **k: msgs.append(m))
    assert any("Недостаточно" in m for m in msgs)
    db.refresh(u)
    assert u.stitches_balance == 50
