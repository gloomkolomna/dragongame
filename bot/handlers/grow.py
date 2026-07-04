"""Growing step handler — crosses count + norm/punish flow."""

import json
import os
import re
from bot.fsm import IDLE, grow_state, step_from_state, is_waiting_text, state_mode
from bot.services.grow_service import (
    get_dragon_step, get_total_steps, complete_step, complete_dragon,
    get_timeout_remaining, set_step_timeout, get_step_timeout,
)
from bot.keyboard import step_buttons_keyboard, growing_keyboard

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


def handle_grow_command(user, db, send_message, upload_image=None):
    if not user.current_dragon_id:
        send_message("Нет активного дракона. Добавь нового.")
        user.state = IDLE
        db.commit()
        return

    remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"⏳ Дракон отдыхает. Осталось: {hours} ч. {minutes} мин."
        )
        return

    from models import Dragon
    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    step = user.current_step
    total = get_total_steps(db, user.current_dragon_id)
    step_def = get_dragon_step(db, user.current_dragon_id, step)

    if not step_def:
        send_message("Шаг не найден. Возможно, дракон был изменён.")
        return

    msg = format_step(step_def, step, total)
    msg += f"\n\nНорма крестиков: {step_def.crosses_norm}\n"
    msg += "Выбери режим:"
    send_message(msg, keyboard=step_buttons_keyboard())


def handle_norm_command(user, db, send_message):
    if not user.current_dragon_id:
        send_message("Нет активного дракона.")
        return

    user.state = grow_state(user.current_step, "norm")
    db.commit()

    step_def = get_dragon_step(db, user.current_dragon_id, user.current_step)
    norm = step_def.crosses_norm if step_def else 1000
    send_message(
        f"✅ Режим «Норма» — нужно вышить не менее {norm} крестиков.\n"
        f"Когда закончишь, отправь сообщение «вышито {norm}» (или другое число)."
    )


def handle_x2_command(user, db, send_message):
    if not user.current_dragon_id:
        send_message("Нет активного дракона.")
        return

    user.state = grow_state(user.current_step, "x2")
    db.commit()

    step_def = get_dragon_step(db, user.current_dragon_id, user.current_step)
    norm = (step_def.crosses_norm if step_def else 1000) * 2
    send_message(
        f"⚠ Режим «Штраф (x2)» — нужно вышить не менее {norm} крестиков.\n"
        f"Когда закончишь, отправь сообщение «вышито {norm}» (или другое число)."
    )


def handle_grow_message(user, text, attachments, db, send_message, upload_image=None):
    if not user.current_dragon_id:
        send_message("Нет активного дракона.")
        user.state = IDLE
        user.current_step = 0
        db.commit()
        return True

    if is_waiting_text(user.state):
        return _handle_crosses_check(user, text, db, send_message, upload_image)

    return True


def _handle_crosses_check(user, text, db, send_message, upload_image=None):
    mode = state_mode(user.state)
    step = user.current_step
    dragon_id = user.current_dragon_id

    remaining = get_timeout_remaining(db, user.vk_id, dragon_id)
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

    text_lower = text.lower()
    if "вышито" not in text_lower:
        send_message('Пожалуйста, отправьте сообщение в формате: «вышито [число]»')
        db.commit()
        return True

    numbers = re.findall(r"\d+", text)
    if not numbers:
        send_message('Пожалуйста, отправьте сообщение в формате: «вышито [число]»')
        db.commit()
        return True

    crosses = int(numbers[0])
    step_def = get_dragon_step(db, dragon_id, step)
    base_norm = step_def.crosses_norm if step_def else 1000
    required = base_norm * 2 if mode == "x2" else base_norm

    if crosses < required:
        send_message(
            f"❌ Вы вышили {crosses} крестиков, а нужно не менее {required}.\n"
            f"Вышивайте дальше и отправьте повторно «вышито [число]»."
        )
        db.commit()
        return True

    complete_step(db, user.vk_id, dragon_id, step)
    total = get_total_steps(db, dragon_id)
    from models import Dragon
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()

    if step >= total:
        step_hours, step_minutes = get_step_timeout(db, dragon_id, step)
        total_timeout_min = step_hours * 60 + step_minutes

        if total_timeout_min > 0:
            set_step_timeout(db, user.vk_id, dragon_id, step)
            next_step = step + 1
            user.state = grow_state(next_step)
            user.current_step = next_step
            send_message(
                f"✅ Шаг {step} выполнен! Дракон будет готов через {step_hours} ч. {step_minutes} мин. Я уведомлю тебя."
            )
            db.commit()
            return True

        complete_dragon(db, user.vk_id, dragon_id)
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

        import json as j
        keyboard = j.dumps({
            "one_time": True,
            "buttons": [
                [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.com/app54663330"}}],
                [{"action": {"type": "text", "label": "🐉 Добавить дракона", "payload": j.dumps({"cmd": "pin"}, ensure_ascii=False)}, "color": "primary"}],
                [{"action": {"type": "text", "label": "🔄 Сменить дракона", "payload": j.dumps({"cmd": "garden"}, ensure_ascii=False)}, "color": "secondary"},
                 {"action": {"type": "text", "label": "❓ Помощь", "payload": j.dumps({"cmd": "help"}, ensure_ascii=False)}, "color": "secondary"}],
            ],
        }, ensure_ascii=False)

        attachment = ""
        if upload_image and dragon and dragon.dragon_path:
            filepath = os.path.join(_IMAGES, os.path.basename(dragon.dragon_path))
            attachment = upload_image(filepath)

        send_message(msg, attachment=attachment, keyboard=keyboard)
    else:
        step_hours, step_minutes = get_step_timeout(db, dragon_id, step)
        total_timeout_min = step_hours * 60 + step_minutes

        next_step = step + 1
        user.current_step = next_step

        if total_timeout_min > 0:
            set_step_timeout(db, user.vk_id, dragon_id, step)
            user.state = grow_state(next_step)
            send_message(
                f"✅ Шаг {step} выполнен! Следующий этап будет доступен через {step_hours} ч. {step_minutes} мин."
            )
        else:
            user.state = grow_state(next_step)
            next_def = get_dragon_step(db, dragon_id, next_step)
            msg = f"✅ Шаг {step} выполнен!\n\n"
            if next_def:
                msg += format_step(next_def, next_step, total)
                msg += f"\n\nНорма крестиков: {next_def.crosses_norm}\nВыбери режим:"
            send_message(msg, keyboard=step_buttons_keyboard())

    db.commit()
    return True
