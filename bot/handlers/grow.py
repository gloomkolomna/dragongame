"""Growing step handler — crosses count + norm/punish flow."""

import json
import os
import re
from bot.fsm import IDLE, grow_state, step_from_state, is_waiting_text, state_mode
from bot.services.grow_service import (
    get_dragon_step, get_total_steps, complete_step, complete_dragon,
    get_timeout_remaining, set_step_timeout, get_step_timeout, rarity_name, rarity_stars,
    credit_stitches, is_suspicious, is_blocked, create_suspicious_report, notify_admin,
)
from bot.keyboard import step_buttons_keyboard, growing_keyboard, waiting_keyboard

_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")


def _upload_rel(db, user, rel_path, upload_image):
    if not upload_image or not rel_path:
        return ""
    filepath = os.path.join(_IMAGES, os.path.basename(rel_path))
    if not os.path.isfile(filepath):
        return ""
    def log_err(msg, tb=""):
        from datetime import datetime
        from models import ErrorLog
        db.add(ErrorLog(source="bot", error_type="UPLOAD", message=f"{msg} (file={filepath})", user_id=user.vk_id, traceback_text=tb, created_at=datetime.now().isoformat()))
        db.commit()
    return upload_image(filepath, log_error=log_err, peer_id=user.vk_id)


def step_attachment(db, user, dragon, step_def, upload_image):
    rel = ""
    if step_def and getattr(step_def, "image_path", ""):
        rel = step_def.image_path
    elif dragon and dragon.egg_path:
        rel = dragon.egg_path
    return _upload_rel(db, user, rel, upload_image)


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
        send_message("Нет активных яиц дракона для выращивания. Добавь новое яйцо для выращивания.")
        user.state = IDLE
        db.commit()
        return

    remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"⏳ Яйцо в процессе выращивания. Осталось: {hours} ч. {minutes} мин."
        )
        return

    from models import Dragon
    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    step = user.current_step
    total = get_total_steps(db, user.current_dragon_id)
    step_def = get_dragon_step(db, user.current_dragon_id, step)

    if not step_def:
        send_message("Шаг не найден. Возможно, яйцо дракона было изменено.")
        return

    msg = format_step(step_def, step, total)
    msg += f"\n\nНорма стежков: {step_def.crosses_norm}\n"
    msg += "Выбери режим:"

    attachment = step_attachment(db, user, dragon, step_def, upload_image)

    send_message(msg, attachment=attachment, keyboard=step_buttons_keyboard())


def handle_norm_command(user, db, send_message):
    if not user.current_dragon_id:
        send_message("Нет активного яйца дракона для выращивания.")
        return

    remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"⏳ Яйцо в процессе выращивания. Осталось: {hours} ч. {minutes} мин."
        )
        return

    user.state = grow_state(user.current_step, "norm")
    db.commit()

    step_def = get_dragon_step(db, user.current_dragon_id, user.current_step)
    norm = step_def.crosses_norm if step_def else 1000
    send_message(
        f"✅ Режим «Норма» — нужно вышить не менее {norm} стежков.\n"
        f"Когда закончишь, отправь одним сообщением:\n"
        f"• фото работы (коллаж ДО + ПОСЛЕ + превью)\n"
        f"• текст: «вышито {norm}» (или другое число)",
        keyboard=waiting_keyboard(),
    )


def handle_x2_command(user, db, send_message):
    if not user.current_dragon_id:
        send_message("Нет активного яйца дракона для выращивания.")
        return

    remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"⏳ Яйцо в процессе выращивания. Осталось: {hours} ч. {minutes} мин."
        )
        return

    user.state = grow_state(user.current_step, "x2")
    db.commit()

    step_def = get_dragon_step(db, user.current_dragon_id, user.current_step)
    norm = (step_def.crosses_norm if step_def else 1000) * 2
    send_message(
        f"⚠ Режим «Штраф (x2)» — нужно вышить не менее {norm} стежков.\n"
        f"Когда закончишь, отправь одним сообщением:\n"
        f"• фото работы (коллаж ДО + ПОСЛЕ + превью)\n"
        f"• текст: «вышито {norm}» (или другое число)",
        keyboard=waiting_keyboard(),
    )


def handle_back_command(user, db, send_message, upload_image=None):
    if not is_waiting_text(user.state):
        return
    user.state = grow_state(user.current_step)
    db.commit()
    handle_grow_command(user, db, send_message, upload_image)


def handle_grow_message(user, text, attachments, db, send_message, upload_image=None):
    if not user.current_dragon_id:
        send_message("Нет активного яйца дракона для выращивания.")
        user.state = IDLE
        user.current_step = 0
        db.commit()
        return True

    if is_waiting_text(user.state):
        return _handle_crosses_check(user, text, attachments, db, send_message, upload_image)

    return True


def _handle_crosses_check(user, text, attachments, db, send_message, upload_image=None):
    mode = state_mode(user.state)
    step = user.current_step
    dragon_id = user.current_dragon_id

    remaining = get_timeout_remaining(db, user.vk_id, dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"⏳ Яйцо выращивается. "
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
            f"❌ Вы вышили {crosses} стежков, а нужно не менее {required}.\n"
            f"Вышивайте дальше и отправьте повторно фото работы (можно одним коллажем ДО + ПОСЛЕ + превью) и «вышито [число]»."
        )
        db.commit()
        return True

    photo_infos = [a["photo"] for a in attachments if a.get("type") == "photo" and a.get("photo")]
    if len(photo_infos) == 0:
        send_message(
            "❌ Прикрепи фото работы (можно одним коллажем ДО + ПОСЛЕ + превью) "
            "вместе с текстом «вышито [число]»."
        )
        db.commit()
        return True

    def fmt_photo(p):
        return f"photo{p['owner_id']}_{p['id']}"

    photo_before_id = fmt_photo(photo_infos[0])
    photo_after_id = fmt_photo(photo_infos[1]) if len(photo_infos) > 1 else ""

    if is_blocked(crosses, required):
        create_suspicious_report(
            db, user.vk_id, dragon_id, step, crosses, required, mode,
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
            raw_message=text,
        )
        send_message(
            f"⚠ Ты заявил {crosses} стежков при норме {required} — это слишком много.\n"
            "Шаг не засчитан. Отправь, пожалуйста, корректное число."
        )
        db.commit()
        return True

    credit_stitches(db, user.vk_id, crosses)

    if is_suspicious(crosses, required):
        create_suspicious_report(
            db, user.vk_id, dragon_id, step, crosses, required, mode,
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
            raw_message=text,
        )
        send_message(
            "⚠ Твой отчёт кажется подозрительным и отправлен на проверку. "
            "Стежки зачислены в копилку, но администратор может скорректировать баланс."
        )
        notify_admin(
            f"⚠ Подозрительный отчёт от id{user.vk_id}\n"
            f"Дракон #{dragon_id}, шаг {step}, режим {mode}\n"
            f"Заявлено: {crosses}, норма: {required}\n"
            f"https://vk.ru/gim239999455/convo/{user.vk_id}"
        )

    complete_step(
        db, user.vk_id, dragon_id, step,
        photo_before_id=photo_before_id,
        photo_after_id=photo_after_id,
    )
    total = get_total_steps(db, dragon_id)
    from models import Dragon
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    family_name = ""
    if dragon and dragon.family_id:
        from models import Family
        family = db.query(Family).filter(Family.id == dragon.family_id).first()
        if family:
            family_name = family.name

    if step >= total:
        step_hours, step_minutes = get_step_timeout(db, dragon_id, step)
        total_timeout_min = step_hours * 60 + step_minutes

        if total_timeout_min > 0:
            set_step_timeout(db, user.vk_id, dragon_id, step)
            next_step = step + 1
            user.state = grow_state(next_step)
            user.current_step = next_step
            send_message(
                f"✅ Шаг {step} выращивания яйца дракона выполнен! Дракон будет готов через {step_hours} ч. {step_minutes} мин. Я уведомлю тебя.",
                keyboard=growing_keyboard(),
            )
            db.commit()
            return True

        treasure, family_treasures = complete_dragon(db, user.vk_id, dragon_id)
        user.state = IDLE
        user.current_dragon_id = None
        user.current_step = 0
        msg = (
            f"🎉 Поздравляю! Ты вырастил дракона!\n\n"
            f"🐲 {dragon.name if dragon else '???'} 🐲\n"
            f"Редкость: {rarity_name(dragon.rarity if dragon else 1)} {rarity_stars(dragon.rarity if dragon else 1)}\n"
        )
        if family_name:
            msg += f"Коллекция: {family_name}\n"
        if dragon and dragon.description:
            msg += f"\n{dragon.description}\n"
        msg += "\nЗагляни в мини-приложение Мой Бестиарий, чтобы увидеть его в своей коллекции!"

        import json as j
        from bot.services.legend_service import get_legend_total
        has_legend = dragon and dragon.rarity == 3 and get_legend_total(db, dragon_id) > 0
        legend_rows = []
        if has_legend:
            msg += (
                "\n\n📖 У этого дракона есть легенда — нажми «🐲 Рассказать легенду», чтобы открыть её."
                "\nСобранные легенды можно перечитать в разделе «📖 Библиотека» мини-приложения."
            )
            legend_rows.append([{"action": {"type": "text", "label": "🐲 Рассказать легенду", "payload": j.dumps({"cmd": "legend", "dragon_id": dragon_id}, ensure_ascii=False)}, "color": "primary"}])

        keyboard = j.dumps({
            "one_time": True,
            "buttons": legend_rows + [
                [{"action": {"type": "text", "label": "📖 Список Бестиария", "payload": j.dumps({"cmd": "garden"}, ensure_ascii=False)}, "color": "primary"},
                 {"action": {"type": "text", "label": "❓ Помощь", "payload": j.dumps({"cmd": "help"}, ensure_ascii=False)}, "color": "secondary"}],
                [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.ru/app54663330"}}],
            ],
        }, ensure_ascii=False)

        attachment = ""
        if upload_image and dragon and dragon.dragon_path:
            filepath = os.path.join(_IMAGES, os.path.basename(dragon.dragon_path))
            def log_err(msg, tb=""):
                from datetime import datetime
                from models import ErrorLog
                db.add(ErrorLog(source="bot", error_type="UPLOAD", message=f"{msg} (file={filepath})", user_id=user.vk_id, traceback_text=tb, created_at=datetime.now().isoformat()))
                db.commit()
            attachment = upload_image(filepath, log_error=log_err, peer_id=user.vk_id)

        send_message(msg, attachment=attachment, keyboard=keyboard)

        if treasure:
            t_msg = f"💎 В твоей пещере появилось новое сокровище!\nПосмотри его в мини-приложении Мой Бестиарий.\n\nПолучено: {treasure.name}"
            if treasure.description:
                t_msg += f"\n{treasure.description}"
            t_attach = ""
            if upload_image and treasure.image_path:
                t_filepath = os.path.join(_IMAGES, os.path.basename(treasure.image_path))
                if os.path.isfile(t_filepath):
                    def log_err_t(msg, tb=""):
                        from datetime import datetime
                        from models import ErrorLog
                        db.add(ErrorLog(source="bot", error_type="UPLOAD", message=f"{msg} (file={t_filepath})", user_id=user.vk_id, traceback_text=tb, created_at=datetime.now().isoformat()))
                        db.commit()
                    t_attach = upload_image(t_filepath, log_error=log_err_t, peer_id=user.vk_id)
            send_message(t_msg, attachment=t_attach)

        for ft in (family_treasures or []):
            ft_msg = f"💎 В твоей пещере появилось новое сокровище!\nПосмотри его в мини-приложении Мой Бестиарий.\n\nСокровище семьи: {ft.name}"
            if ft.description:
                ft_msg += f"\n{ft.description}"
            ft_attach = ""
            if upload_image and ft.image_path:
                ft_filepath = os.path.join(_IMAGES, os.path.basename(ft.image_path))
                if os.path.isfile(ft_filepath):
                    ft_attach = upload_image(ft_filepath, log_error=lambda msg, tb="": None, peer_id=user.vk_id)
            send_message(ft_msg, attachment=ft_attach)

        from services.epic_service import maybe_spawn_first_epic
        epic = maybe_spawn_first_epic(db, user.vk_id)
        if epic:
            from bot.handlers.epic import send_epic_spawn_notice
            send_epic_spawn_notice(epic, user, db, send_message, upload_image)
    else:
        step_hours, step_minutes = get_step_timeout(db, dragon_id, step)
        total_timeout_min = step_hours * 60 + step_minutes

        next_step = step + 1
        user.current_step = next_step

        if total_timeout_min > 0:
            set_step_timeout(db, user.vk_id, dragon_id, step)
            user.state = grow_state(next_step)
            send_message(
                f"✅ Шаг {step} выращивания яйца дракона выполнен! Следующий этап будет доступен через {step_hours} ч. {step_minutes} мин.",
                keyboard=growing_keyboard(),
            )
        else:
            user.state = grow_state(next_step)
            next_def = get_dragon_step(db, dragon_id, next_step)
            msg = f"✅ Шаг {step} выполнен!\n\n"
            if next_def:
                msg += format_step(next_def, next_step, total)
                msg += f"\n\n🎯 Норма стежков: {next_def.crosses_norm}\nВыбери режим:"
            attachment = step_attachment(db, user, dragon, next_def, upload_image)
            send_message(msg, attachment=attachment, keyboard=step_buttons_keyboard())

    db.commit()
    return True
