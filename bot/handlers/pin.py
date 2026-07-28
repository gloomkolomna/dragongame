"""PIN entry handler."""

import json
import os
from bot.fsm import AWAIT_PIN, AWAIT_PIN_LIST, IDLE, grow_state
from bot.services.pin_service import validate_pin_code, activate_pin, activate_all_reservations, activate_pin_silently
from bot.keyboard import start_growing_keyboard, await_garden_keyboard, await_pin_list_keyboard, row, bestiary_link_row, buy_eggs_row, _keyboard as kb_json

_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")


def handle_pin_command(user, db, send_message):
    was_growing = user.current_dragon_id is not None
    _restore_pin_list_prev_state(user)
    user.state = AWAIT_PIN
    db.commit()

    if was_growing:
        send_message("🔑 У тебя уже есть активный дракон — сейчас добавим ещё одного.\nВведи 5-символьный PIN-код с листка из яйца (заглавные буквы и цифры):")
    else:
        send_message("🔑 Введи 5-символьный PIN-код с листка из нового яйца (заглавные буквы и цифры):")


def _save_pin_list_prev_state(user):
    if user.state != AWAIT_PIN_LIST:
        sd = json.loads(user.state_data or "{}")
        sd["_pin_list_prev_state"] = user.state
        user.state_data = json.dumps(sd, ensure_ascii=False)


def _restore_pin_list_prev_state(user):
    sd = json.loads(user.state_data or "{}")
    prev_state = sd.pop("_pin_list_prev_state", None)
    sd.pop("_pin_list", None)
    user.state_data = json.dumps(sd, ensure_ascii=False)
    return prev_state


def handle_my_pins(user, db, send_message):
    from models import DragonReservation, Dragon

    reservations = (
        db.query(DragonReservation)
        .filter(
            DragonReservation.vk_user_id == user.vk_id,
            DragonReservation.is_activated == False,
        )
        .order_by(DragonReservation.created_at.desc())
        .all()
    )

    reservation_ids = [r.dragon_id for r in reservations]
    _save_pin_list_prev_state(user)
    sd = json.loads(user.state_data or "{}")
    sd["_pin_list"] = reservation_ids
    user.state_data = json.dumps(sd, ensure_ascii=False)
    user.state = AWAIT_PIN_LIST
    db.commit()

    if not reservations:
        send_message(
            "\U0001f511 У тебя пока нет неактивированных PIN-кодов.\n\n"
            "PIN-коды появляются здесь после покупки яиц или получения бесплатных.",
            keyboard=await_pin_list_keyboard(),
        )
        return

    lines = ["\U0001f511 Твои неактивированные PIN-коды:\n"]
    for i, r in enumerate(reservations, 1):
        dragon = db.query(Dragon).filter(Dragon.id == r.dragon_id).first()
        lines.append(f"{i}. {dragon.pin_code if dragon else '—'}")
    if len(reservations) >= 2:
        lines.append("\nОтправь номер из списка (например «1»), чтобы активировать яйцо.")
        lines.append("Или несколько через запятую: «1,3,5».")
    lines.append("Или нажми «\u26a1 Активировать все».")

    send_message("\n".join(lines), keyboard=await_pin_list_keyboard())


def handle_pin_entry(user, text, db, send_message, upload_image=None):
    from datetime import datetime
    from models import ErrorLog

    code = text.strip().upper()

    if len(code) != 5 or not code.isalnum():
        send_message("❌ PIN-код должен быть ровно из 5 символов (заглавные буквы A-Z и цифры). Попробуй ещё раз.")
        return

    dragon = validate_pin_code(db, code)
    if not dragon:
        send_message("❌ PIN-код не найден. Проверь цифры и попробуй ещё раз.")
        return

    from models import DragonReservation, UserDragon
    already_owned = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id,
        UserDragon.dragon_id == dragon.id,
    ).first()

    if not already_owned:
        reservation = db.query(DragonReservation).filter(
            DragonReservation.dragon_id == dragon.id,
            DragonReservation.vk_user_id == user.vk_id,
            DragonReservation.is_activated == False,
        ).first()

        if not reservation:
            from bot.services.grow_service import create_suspicious_report, notify_admin
            create_suspicious_report(
                db, user.vk_id, dragon.id, 0, 0, 0, "pin_no_reservation",
                raw_message=text,
            )
            import config
            notify_admin(
                f"🔑 Подозрительная активация PIN без брони от id{user.vk_id}\n"
                f"Дракон #{dragon.id} ({dragon.egg_type or '?'})\n"
                f"PIN: {code}\n"
                f"https://vk.ru/gim{config.VK_GROUP_ID}/convo/{user.vk_id}"
            )

    ok = activate_pin(db, user.vk_id, dragon)
    if not ok:
        send_message("⚠️ Ты уже активировал это яйцо дракона. Попробуй другой PIN-код.")
        db.commit()
        return

    user.current_dragon_id = dragon.id
    user.current_step = 1
    user.state = grow_state(1)
    db.commit()

    msg = f"🥚 В твоей коллекции появилось новое яйцо дракона!\n\n"
    if dragon.egg_type:
        msg += f"Тип: {dragon.egg_type}\n"

    attachment = ""
    if not upload_image:
        db.add(ErrorLog(source="bot", error_type="PIN", message=f"upload_image not provided (egg_path={dragon.egg_path})", user_id=user.vk_id, created_at=datetime.now().isoformat()))
        db.commit()
    elif not dragon.egg_path:
        db.add(ErrorLog(source="bot", error_type="PIN", message=f"egg_path is empty for dragon {dragon.id}", user_id=user.vk_id, created_at=datetime.now().isoformat()))
        db.commit()
    else:
        filepath = os.path.join(_IMAGES, os.path.basename(dragon.egg_path))
        if not os.path.isfile(filepath):
            db.add(ErrorLog(source="bot", error_type="PIN", message=f"Image not found: {filepath} (egg_path={dragon.egg_path})", user_id=user.vk_id, created_at=datetime.now().isoformat()))
            db.commit()
        else:
            def log_err(msg, tb=""):
                db.add(ErrorLog(source="bot", error_type="PIN", message=f"Upload failed for {filepath}: {msg}", user_id=user.vk_id, traceback_text=tb, created_at=datetime.now().isoformat()))
                db.commit()
            attachment = upload_image(filepath, log_error=log_err, peer_id=user.vk_id)
            if not attachment:
                db.add(ErrorLog(source="bot", error_type="PIN", message=f"Upload returned empty for: {filepath}", user_id=user.vk_id, created_at=datetime.now().isoformat()))
                db.commit()

    keyboard = start_growing_keyboard()
    send_message(msg, attachment=attachment, keyboard=keyboard)


def handle_activate_all(user, db, send_message):
    from models import DragonReservation

    reservations = (
        db.query(DragonReservation)
        .filter(
            DragonReservation.vk_user_id == user.vk_id,
            DragonReservation.is_activated == False,
        )
        .all()
    )

    if not reservations:
        send_message("\u26a1 У тебя нет неактивированных яиц.")
        return

    activated, total = activate_all_reservations(db, user.vk_id)

    prev_state = _restore_pin_list_prev_state(user)
    if prev_state and prev_state != AWAIT_PIN_LIST:
        user.state = prev_state
    else:
        user.state = IDLE
    db.commit()

    if activated == 0:
        send_message("\u26a0\ufe0f Все яйца уже были активированы ранее.")
        return

    send_message(
        f"\u2705 Активировано яиц: {activated} из {total}.\n\n"
        f"Все новые яйца добавлены в твою коллекцию. "
        f"Открой \u00ab\U0001f4d6 Список Бестиария\u00bb, чтобы их увидеть.",
        keyboard=kb_json([
            row(("\U0001f4d6 Список Бестиария", "garden")),
            buy_eggs_row(),
            bestiary_link_row(),
        ]),
    )


def handle_activate_by_number(user, text, db, send_message):
    from models import DragonReservation, Dragon

    if user.state != AWAIT_PIN_LIST:
        return False

    sd = json.loads(user.state_data or "{}")
    pin_list = sd.get("_pin_list", [])
    if not pin_list:
        return False

    raw = text.strip().replace(" ", "")
    parts = raw.split(",")
    numbers = []
    for p in parts:
        try:
            n = int(p)
            if 1 <= n <= len(pin_list):
                numbers.append(n)
        except ValueError:
            pass

    if not numbers:
        return False

    activated = 0
    failed = 0
    for n in numbers:
        dragon_id = pin_list[n - 1]
        dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
        if dragon and activate_pin_silently(db, user.vk_id, dragon):
            activated += 1
        else:
            failed += 1

    prev_state = _restore_pin_list_prev_state(user)
    if prev_state and prev_state != AWAIT_PIN_LIST:
        user.state = prev_state
    else:
        user.state = IDLE
    db.commit()

    parts = []
    if activated > 0:
        parts.append(f"\u2705 Активировано: {activated}")
    if failed > 0:
        parts.append(f"\u26a0\ufe0f Пропущено (уже активированы): {failed}")
    parts.append("")
    parts.append("Открой \u00ab\U0001f4d6 Список Бестиария\u00bb, чтобы увидеть новые яйца.")

    send_message("\n".join(parts), keyboard=kb_json([
        row(("\U0001f4d6 Список Бестиария", "garden")),
        buy_eggs_row(),
        bestiary_link_row(),
    ]))
    return True


def cancel_pin_list(user, db, send_message, upload_image=None):
    prev_state = _restore_pin_list_prev_state(user)
    if prev_state and prev_state != AWAIT_PIN_LIST:
        user.state = prev_state
    else:
        user.state = IDLE
    db.commit()

    if prev_state and (prev_state.startswith("epic_egg_") or prev_state.startswith("epic_care_")
                       or prev_state in ("await_epic_name", "await_epic_restart", "await_epic_egg_intro")):
        from bot.handlers.epic import handle_epic_command
        handle_epic_command(user, db, send_message, upload_image)
        return

    if user.current_dragon_id:
        from bot.services.grow_service import get_timeout_remaining, get_dragon_step, get_total_steps
        from models import Dragon
        from bot.keyboard import step_buttons_keyboard
        dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
        remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
        if remaining is not None:
            total_secs = int(remaining.total_seconds())
            hours, remainder = divmod(total_secs, 3600)
            minutes = remainder // 60
            label = dragon.egg_type if dragon else "яйцо"
            send_message(
                f"\U0001f95a Яйцо «{label}» выращивается.\n\u23f3 Осталось: {hours} ч. {minutes} мин."
            )
            return
        user.state = grow_state(user.current_step)
        db.commit()
        total = get_total_steps(db, user.current_dragon_id)
        step_def = get_dragon_step(db, user.current_dragon_id, user.current_step)
        label = dragon.egg_type if dragon else "яйцо"
        msg = f"\U0001f95a {label}\n\U0001f4cb Шаг {user.current_step} из {total}"
        if step_def:
            msg += f"\n\n\U0001f3af Норма: {step_def.crosses_norm} стежков\nВыбери режим:"
        send_message(msg, keyboard=step_buttons_keyboard())
        return

    from bot.keyboard import idle_keyboard
    send_message(
        "\U0001f511 Раздел PIN-кодов закрыт.",
        keyboard=idle_keyboard(),
    )
