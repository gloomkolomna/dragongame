"""Shop logic: stage resolution, listing, inventory, purchase. Pure DB, no VK."""

from datetime import datetime
from models import (
    User, UserDragon, ShopItem, StageShopItem, UserInventory,
    EpicCareState, EpicStage,
)


def get_current_stage_key(db, vk_id: int):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or not user.epic_dragon_id:
        return None
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == user.epic_dragon_id
    ).first()
    if not ud:
        return None
    care = db.query(EpicCareState).filter(EpicCareState.user_dragon_id == ud.id).first()
    if care and care.stage_id:
        stage = db.query(EpicStage).filter(EpicStage.id == care.stage_id).first()
        if stage:
            return f"epic:{stage.dragon_id}:{stage.stage_number}"
    return f"epic:{user.epic_dragon_id}:egg"


def get_stage_items(db, stage_key):
    if not stage_key:
        return []
    links = (
        db.query(StageShopItem)
        .filter(StageShopItem.stage_key == stage_key)
        .order_by(StageShopItem.sort_order, StageShopItem.id)
        .all()
    )
    result = []
    for link in links:
        item = db.query(ShopItem).filter(
            ShopItem.id == link.item_id, ShopItem.is_active == True
        ).first()
        if item:
            result.append(item)
    return result


def get_inventory(db, vk_id: int):
    rows = db.query(UserInventory).filter(UserInventory.user_id == vk_id).all()
    result = []
    for inv in rows:
        item = db.query(ShopItem).filter(ShopItem.id == inv.item_id).first()
        if item:
            result.append((item, inv.quantity))
    return result


def owns_item(db, vk_id: int, item_id: int) -> bool:
    return db.query(UserInventory).filter(
        UserInventory.user_id == vk_id, UserInventory.item_id == item_id
    ).first() is not None


def purchase(db, vk_id: int, item_id: int) -> dict:
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        return {"status": "not_found"}
    item = db.query(ShopItem).filter(
        ShopItem.id == item_id, ShopItem.is_active == True
    ).first()
    if not item:
        return {"status": "not_found"}
    stage_key = get_current_stage_key(db, vk_id)
    stage_item_ids = {i.id for i in get_stage_items(db, stage_key)}
    if item.id not in stage_item_ids:
        return {"status": "not_on_stage", "item": item}
    if owns_item(db, vk_id, item_id):
        return {"status": "already", "item": item}
    balance = user.stitches_balance or 0
    if balance < item.cost_stitches:
        return {"status": "insufficient", "item": item, "balance": balance}
    user.stitches_balance = balance - item.cost_stitches
    db.add(UserInventory(
        user_id=vk_id, item_id=item_id, quantity=1,
        acquired_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    ))
    db.commit()
    return {"status": "ok", "item": item, "balance": user.stitches_balance}
