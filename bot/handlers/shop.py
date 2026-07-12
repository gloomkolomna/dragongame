"""Shop handler — browse stage items and buy (bot-only purchase)."""

PAGE_SIZE = 5


def handle_shop_command(user, db, send_message, page=0):
    from services.shop_service import get_current_stage_key, get_stage_items, get_inventory
    from bot.keyboard import shop_keyboard

    stage_key = get_current_stage_key(db, user.vk_id)
    if not stage_key:
        send_message("🛒 Магазин откроется, когда у тебя появится эпический дракон.")
        return

    items = get_stage_items(db, stage_key)
    if not items:
        send_message("🛒 Пока на этой стадии нет товаров.")
        return

    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    page_items = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    owned_ids = {it.id for it, _ in get_inventory(db, user.vk_id)}

    lines = [f"🛒 Магазин\n✚ Крестиков в копилке: {user.stitches_balance or 0}", ""]
    for it in page_items:
        owned = " ✅ куплено" if it.id in owned_ids else ""
        lines.append(f"• {it.name} — {it.cost_stitches} крестиков{owned}")
        if it.description:
            lines.append(f"  {it.description}")
    if total_pages > 1:
        lines.append(f"\nСтраница {page + 1}/{total_pages}")

    buyable = [it for it in page_items if it.id not in owned_ids]
    send_message("\n".join(lines), keyboard=shop_keyboard(buyable, page, total_pages))


def handle_buy(user, item_id, db, send_message, upload_image=None):
    from services.shop_service import purchase

    res = purchase(db, user.vk_id, item_id)
    status = res.get("status")
    if status == "ok":
        send_message(f"✅ Куплено: {res['item'].name}. Осталось крестиков: {res['balance']}.")
        from bot.handlers.epic import handle_epic_command
        handle_epic_command(user, db, send_message, upload_image)
        return
    elif status == "already":
        send_message(f"Ты уже купил «{res['item'].name}» на этой стадии.")
    elif status == "insufficient":
        send_message(
            f"❌ Недостаточно крестиков: нужно {res['item'].cost_stitches}, "
            f"у тебя {res['balance']}."
        )
    elif status == "not_on_stage":
        send_message("Этот товар недоступен на твоей текущей стадии.")
    else:
        send_message("Товар не найден.")
        return

    handle_shop_command(user, db, send_message)


def handle_inventory(user, db, send_message):
    from services.shop_service import get_inventory
    from bot.keyboard import inventory_keyboard

    inv = get_inventory(db, user.vk_id)
    if not inv:
        send_message(
            "🎒 Твой инвентарь пуст.\nКупи предметы в магазине, чтобы заботиться об эпическом драконе.",
            keyboard=inventory_keyboard(),
        )
        return

    lines = ["🎒 Мой инвентарь\n"]
    for item, qty in inv:
        lines.append(f"• {item.name} — {qty} шт.")
    send_message("\n".join(lines), keyboard=inventory_keyboard())
