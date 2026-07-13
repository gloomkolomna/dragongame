from bot.fsm import IDLE, AWAIT_INCUBATOR, is_growing, grow_state
from bot.keyboard import incubator_keyboard
import json as j


def handle_incubator(user, db, send_message, upload_image=None):
    from services.epic_service import get_incubator_epics, has_completed_regular_dragon
    from models import Dragon

    if not has_completed_regular_dragon(db, user.vk_id):
        send_message("🥚 Инкубатор станет доступен после того, как ты вырастишь первого обычного дракона.")
        return

    epics = get_incubator_epics(db, user.vk_id)
    pool = db.query(Dragon).filter(Dragon.is_epic == True).all()
    if not pool:
        send_message("🐲 Эпических драконов пока нет в игре.")
        return
    sd = j.loads(user.state_data or "{}")
    sd["_inc_prev_state"] = user.state
    user.state_data = j.dumps(sd, ensure_ascii=False)
    user.state = AWAIT_INCUBATOR
    db.commit()
    lines = ["🥚 Инкубатор — выбери эпическое яйцо:\n"]
    for i, ep in enumerate(epics, start=1):
        d = ep["dragon"]
        status = ep["status"]
        cost = ep["cost"]
        is_active = ep["is_active"]
        marker = " 👈 сейчас" if is_active else ""
        if status == "completed":
            lines.append(f"{i}. 🔄 {d.egg_type or d.name} — выращен, можно повторить за {cost} ✚{marker}")
        elif status == "growing":
            lines.append(f"{i}. 🐣 {d.egg_type or d.name} — уже растёт{marker}")
        else:
            lines.append(f"{i}. 🥚 {d.egg_type or d.name} — {cost} ✚{marker}")
    lines.append("\nНапиши номер яйца или «0» для отмены.")
    send_message("\n".join(lines), keyboard=incubator_keyboard(epics))


def handle_incubator_pick(user, num, db, send_message, upload_image=None):
    from services.epic_service import get_incubator_epics, purchase_epic_egg
    epics = get_incubator_epics(db, user.vk_id)
    if num < 1 or num > len(epics):
        send_message("❌ Неверный номер. Напиши номер из списка или «0» для отмены.")
        return
    ep = epics[num - 1]
    dragon = ep["dragon"]
    status = ep["status"]
    cost = ep["cost"]

    if status == "growing":
        if ep["is_active"]:
            send_message(f"🐣 «{dragon.egg_type or dragon.name}» уже активен. Используй «🐲 Эпический» для продолжения.")
        else:
            user.epic_dragon_id = dragon.id
            db.commit()
            from bot.handlers.epic import handle_epic_command
            handle_epic_command(user, db, send_message, upload_image)
        return

    if cost <= 0:
        send_message("Этот эпический дракон недоступен для покупки.")
        return

    sd = j.loads(user.state_data or "{}")
    sd["_inc_pick_id"] = dragon.id
    user.state_data = j.dumps(sd, ensure_ascii=False)
    db.commit()
    confirm_kb = j.dumps({
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": f"✅ Купить за {cost} ✚", "payload": j.dumps({"cmd": "incubator_confirm"}, ensure_ascii=False)}, "color": "positive"}],
            [{"action": {"type": "text", "label": "◀ Отмена", "payload": j.dumps({"cmd": "incubator_cancel"}, ensure_ascii=False)}, "color": "secondary"}],
        ],
    }, ensure_ascii=False)
    send_message(
        f"🥚 Купить яйцо «{dragon.egg_type or dragon.name}» за {cost} ✚?\n"
        f"У вас: {user.stitches_balance or 0} ✚",
        keyboard=confirm_kb,
    )


def handle_incubator_confirm(user, db, send_message, upload_image=None):
    sd = j.loads(user.state_data or "{}")
    dragon_id = sd.get("_inc_pick_id", 0)
    if not dragon_id:
        send_message("Ошибка: яйцо не выбрано.")
        handle_incubator(user, db, send_message, upload_image)
        return
    ok, message, dragon = purchase_epic_egg(db, user.vk_id, dragon_id)
    if not ok:
        send_message(f"❌ {message}")
        handle_incubator(user, db, send_message, upload_image)
        return
    user.state_data = "{}"
    db.commit()
    send_message(f"✅ {message}")
    from bot.handlers.epic import handle_epic_command
    handle_epic_command(user, db, send_message, upload_image)


def handle_incubator_cancel(user, db, send_message, upload_image=None):
    _restore_state(user, db, send_message, upload_image)


def _restore_state(user, db, send_message, upload_image=None):
    sd = j.loads(user.state_data or "{}")
    prev_state = sd.pop("_inc_prev_state", None)
    sd.pop("_inc_pick_id", None)
    user.state_data = j.dumps(sd, ensure_ascii=False)
    if prev_state and (prev_state.startswith("epic_egg_") or prev_state.startswith("epic_care_") or prev_state in ("await_epic_name", "await_epic_restart")):
        user.state = prev_state
        db.commit()
        from bot.handlers.epic import handle_epic_command
        handle_epic_command(user, db, send_message, upload_image)
        return
    if user.current_dragon_id:
        user.state = grow_state(user.current_step)
    else:
        user.state = IDLE
    db.commit()
    send_message("Хорошо, вернулись.", keyboard=None)


def purchase_epic_egg(db, vk_id, dragon_id):
    from services.epic_service import purchase_epic_egg as _purchase
    return _purchase(db, vk_id, dragon_id)
