"""Growing step handler — exactly 2 photos + keyword in one message."""

import json
import os
from bot.fsm import IDLE, grow_state
from bot.services.grow_service import (
    get_dragon_step, get_total_steps, complete_step, complete_dragon,
    get_timeout_remaining, set_step_timeout, get_step_timeout,
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

    # Timeout check before accepting any submission
    remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"⏳ Этот дракон ещё отдыхает после предыдущего этапа. "
            f"Осталось подождать: {hours} ч. {minutes} мин. Вернитесь позже!"
        )
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

            keyboard = json.dumps({
                "one_time": True,
                "buttons": [
                    [{
                        "action": {
                            "type": "open_link",
                            "label": "📖 Мой Бестиарий",
                            "link": "https://vk.com/app54663330",
                        },
                    }],
                    [
                        {
                            "action": {
                                "type": "text",
                                "label": "🐉 Добавить дракона",
                                "payload": json.dumps({"cmd": "pin"}, ensure_ascii=False),
                            },
                            "color": "primary",
                        },
                    ],
                    [
                        {
                            "action": {
                                "type": "text",
                                "label": "🔄 Сменить дракона",
                                "payload": json.dumps({"cmd": "garden"}, ensure_ascii=False),
                            },
                            "color": "secondary",
                        },
                        {
                            "action": {
                                "type": "text",
                                "label": "❓ Помощь",
                                "payload": json.dumps({"cmd": "help"}, ensure_ascii=False),
                            },
                            "color": "secondary",
                        },
                    ],
                ],
            }, ensure_ascii=False)

            attachment = ""
            if upload_image and dragon and dragon.dragon_path:
                filepath = os.path.join(_IMAGES, os.path.basename(dragon.dragon_path))
                attachment = upload_image(filepath)

            send_message(msg, attachment=attachment, keyboard=keyboard)
        else:
            step_hours, step_minutes = get_step_timeout(db, user.current_dragon_id, step)
            total_timeout_min = step_hours * 60 + step_minutes
            if total_timeout_min > 0:
                set_step_timeout(db, user.vk_id, user.current_dragon_id, step)
                msg = f"✅ Шаг {step} выполнен! Следующий этап будет доступен через {step_hours} ч. {step_minutes} мин. Я уведомлю тебя, когда дракон будет готов."
            else:
                bar_len = 10
                filled = round((step / max(total, 1)) * bar_len)
                bar = "█" * filled + "░" * (bar_len - filled)
                msg = f"✅ Шаг {step} выполнен! {bar} {pct}%\n\n"

            next_step = step + 1
            user.state = grow_state(next_step)
            user.current_step = next_step

            if not total_timeout_min:
                next_def = get_dragon_step(db, user.current_dragon_id, next_step)
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
        remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
        if remaining is not None:
            total_secs = int(remaining.total_seconds())
            hours, remainder = divmod(total_secs, 3600)
            minutes = remainder // 60
            send_message(
                f"⏳ Этот дракон ещё отдыхает после предыдущего этапа. "
                f"Осталось подождать: {hours} ч. {minutes} мин. Вернитесь позже!"
            )
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
