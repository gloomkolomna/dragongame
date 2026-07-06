"""PIN entry handler."""

import os
from bot.fsm import AWAIT_PIN, IDLE, grow_state
from bot.services.pin_service import validate_pin_code, activate_pin
from bot.keyboard import start_growing_keyboard

_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")


def handle_pin_command(user, db, send_message):
    was_growing = user.current_dragon_id is not None
    user.state = AWAIT_PIN
    db.commit()

    if was_growing:
        send_message("🔑 У тебя уже есть активный дракон — сейчас добавим ещё одного.\nВведи 5-символьный PIN-код с листка из яйца (заглавные буквы и цифры):")
    else:
        send_message("🔑 Введи 5-символьный PIN-код с листка из нового яйца (заглавные буквы и цифры):")


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
            def log_err(msg):
                db.add(ErrorLog(source="bot", error_type="PIN", message=f"Upload failed for {filepath}: {msg}", user_id=user.vk_id, created_at=datetime.now().isoformat()))
                db.commit()
            attachment = upload_image(filepath, log_error=log_err, peer_id=user.vk_id)
            if not attachment:
                db.add(ErrorLog(source="bot", error_type="PIN", message=f"Upload returned empty for: {filepath}", user_id=user.vk_id, created_at=datetime.now().isoformat()))
                db.commit()

    keyboard = start_growing_keyboard()
    send_message(msg, attachment=attachment, keyboard=keyboard)
