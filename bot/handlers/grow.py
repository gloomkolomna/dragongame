"""Growing step handler — exactly 2 photos + keyword in one message."""

import os
from bot.fsm import IDLE, grow_state
from bot.services.grow_service import (
    get_dragon_step, get_total_steps, complete_step, complete_dragon,
)

_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")


def format_step(step_def, step_num: int, total: int) -> str:
    lines = [f"📋 Шаг {step_num} из {total}"]
    if step_def and step_def.magic_action:
        lines.append(f"✨ {step_def.magic_action}")
    if step_def and step_def.task_description:
        lines.append(f"📝 {step_def.task_description}")
    if step_def and step_def.hint:
        lines.append(f"💡 {step_def.hint}")
    return "\n".join(lines)


def handle_grow_message(user, text, attachments, db, send_message, upload_image=None):
    if not user.current_dragon_id:
        send_message("Что-то пошло не так — нет активного дракона.")
        user.state = IDLE
        user.current_step = 0
        user.current_dragon_id = None
        db.commit()
        return True

    photo_ids = _extract_photo_ids(attachments)
    photo_count = len(photo_ids)
    has_keyword = "вышито" in text.lower()

    # Step completion: exactly 2 photos + keyword in one message
    if has_keyword and photo_count == 2:
        step = user.current_step
        complete_step(db, user.vk_id, user.current_dragon_id, step, photo_ids[0], photo_ids[1])

        total = get_total_steps(db, user.current_dragon_id)
        pct = round((step / max(total, 1)) * 100)

        from models import Dragon
        dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()

        if step >= total:
            complete_dragon(db, user.vk_id, user.current_dragon_id)
            user.state = IDLE
            user.current_dragon_id = None
            user.current_step = 0

            msg = (
                f"🎉 Поздравляю! Ты вырастил дракона!\n\n"
                f"⭐ {dragon.name if dragon else '???'} ⭐\n"
                f"Редкость: {'⭐' * (dragon.rarity if dragon else 1)}\n"
            )
            if dragon and dragon.description:
                msg += f"\n{dragon.description}\n"
            msg += "\nЗагляни в мини-приложение, чтобы увидеть его в своей коллекции!"

            attachment = ""
            if upload_image and dragon and dragon.dragon_path:
                filepath = os.path.join(_IMAGES, os.path.basename(dragon.dragon_path))
                attachment = upload_image(filepath)

            send_message(msg, attachment=attachment)
        else:
            next_step = step + 1
            user.state = grow_state(next_step)
            user.current_step = next_step

            next_def = get_dragon_step(db, user.current_dragon_id, next_step)
            bar_len = 10
            filled = round((step / max(total, 1)) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)

            msg = f"✅ Шаг {step} выполнен! {bar} {pct}%\n\n"
            if next_def:
                msg += format_step(next_def, next_step, total) + "\n"
            msg += "\nПришли 2 фото (до и после) и напиши «вышито»."

            send_message(msg)

        db.commit()
        return True

    # Anything else — not the correct format
    if has_keyword or photo_count > 0:
        send_message("❌ Нужно ровно 2 фото и слово «вышито» в одном сообщении.")
    else:
        send_message(
            f"📋 Ты на шаге {user.current_step}. "
            f"Пришли 2 фото (до и после) и напиши «вышито» в одном сообщении."
        )

    db.commit()
    return True


def _extract_photo_ids(attachments) -> list[str]:
    ids = []
    if not attachments:
        return ids
    for att in attachments:
        if att.get("type") == "photo":
            photo = att.get("photo", {})
            if isinstance(photo, str):
                ids.append(photo)
                continue
            owner_id = photo.get("owner_id")
            pid = photo.get("id")
            if owner_id is not None and pid is not None:
                ids.append(f"{owner_id}_{pid}")
            elif pid is not None:
                ids.append(str(pid))
    return ids
