"""Command handlers: /start, /help, /status, garden."""

from models import Dragon, UserDragon, UserProgress
from bot.fsm import IDLE, GROW_STEP, AWAIT_GARDEN, step_from_state, grow_state
from bot.services.grow_service import get_total_steps, get_dragon_step, get_timeout_remaining
from bot.handlers.grow import format_step
from bot.keyboard import step_buttons_keyboard


def handle_start(user, db, send_message):
    if user.state == IDLE or not user.current_dragon_id:
        from models import UserDragon
        has_any = db.query(UserDragon).filter(UserDragon.user_id == user.vk_id).first() is not None
        if has_any:
            send_message(
                "🐉 Добро пожаловать в Бестиарий драконьих легенд!\n\n"
                "Здесь ты выращиваешь драконов через вышивку.\n"
                "Купил яйцо? Нажми «🐉 Добавить дракона» и введи PIN-код."
            )
        else:
            send_message(
                "🐉 У тебя пока нет драконов.\n"
                "Нажми «🐉 Добавить дракона» чтобы начать выращивание."
            )
    else:
        dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
        if not dragon:
            from bot.keyboard import idle_keyboard
            user.current_dragon_id = None
            user.current_step = 0
            user.state = IDLE
            db.commit()
            send_message(
                "Дракон не найден. Нажми «🐉 Добавить дракона» чтобы начать.",
                keyboard=idle_keyboard(has_active=False),
            )
            return
        step = user.current_step
        remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
        timeout_line = ""
        if remaining is not None:
            total_secs = int(remaining.total_seconds())
            hours, remainder = divmod(total_secs, 3600)
            minutes = remainder // 60
            timeout_line = f"\n⏳ Следующий шаг будет доступен через: {hours} ч. {minutes} мин."
        else:
            timeout_line = "\n✅ Готов к следующему шагу!"
        step_def = get_dragon_step(db, user.current_dragon_id, step)
        norm = step_def.crosses_norm if step_def else "?"
        send_message(
            f"🪴 Ты выращиваешь: {dragon.egg_type or 'яйцо'}\n"
            f"📋 Текущий шаг: {step}\n"
            f"🎯 Норма крестиков: {norm}\n"
            f"{timeout_line}"
        )


def handle_help(send_message):
    send_message(
        "🐉 Добро пожаловать в Бестиарий драконьих легенд!\n\n"
        "📖 Мой Бестиарий — открыть коллекцию в мини-приложении ВК\n"
        "🐉 Добавить дракона — ввести PIN-код с яйца и начать выращивание\n"
        "🌱 Перейти к выращиванию — начать/продолжить текущий шаг\n"
        "🔄 Сменить дракона — посмотреть всех драконов и переключиться\n"
        "📋 Статус — узнать текущий шаг и прогресс\n"
        "❓ Помощь — эта справка\n\n"
        "📸 Как проходить шаги:\n"
        "1. Нажми «🌱 Перейти к выращиванию»\n"
        "2. Выбери «✅ Норма» или «⚠ Штраф (x2)»\n"
        "3. Вышей нужное количество крестиков\n"
        "4. Отправь сообщение «вышито 1000» (своё число)"
    )


def handle_status(user, db, send_message):
    if not user.current_dragon_id:
        from bot.keyboard import idle_keyboard
        user.state = IDLE
        db.commit()
        send_message(
            "У тебя пока нет активного дракона. Нажми «🐉 Добавить дракона» чтобы начать.",
            keyboard=idle_keyboard(has_active=False),
        )
        return

    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    if not dragon:
        from bot.keyboard import idle_keyboard
        user.current_dragon_id = None
        user.current_step = 0
        user.state = IDLE
        db.commit()
        send_message(
            "Дракон не найден. Нажми «🐉 Добавить дракона» чтобы начать.",
            keyboard=idle_keyboard(has_active=False),
        )
        return

    total = get_total_steps(db, user.current_dragon_id)
    current = user.current_step
    pct = round(((current - 1) / max(total, 1)) * 100) if total else 0
    bar_len = 10
    filled = round(((current - 1) / max(total, 1)) * bar_len) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
    timeout_line = ""
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        timeout_line = f"\n⏳ Следующий шаг будет доступен через: {hours} ч. {minutes} мин."
    else:
        timeout_line = "\n✅ Готов к следующему шагу!"

    step_def = get_dragon_step(db, user.current_dragon_id, current)
    norm = step_def.crosses_norm if step_def else "?"

    send_message(
        f"🥚 {dragon.egg_type or 'яйцо'}\n"
        f"📋 Шаг {current} из {total}\n"
        f"{bar} {pct}%\n"
        f"🎯 Норма: {norm} крестиков\n"
        f"{timeout_line}"
    )


def handle_garden(user, db, send_message):
    entries = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id,
        UserDragon.completed_at == "",
    ).all()

    completed_entries = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id,
        UserDragon.completed_at != "",
    ).all()

    if not entries and not completed_entries:
        from bot.keyboard import idle_keyboard
        user.state = IDLE
        db.commit()
        send_message(
            "🔄 У тебя пока нет драконов. Нажми «🐉 Добавить дракона» чтобы начать.",
            keyboard=idle_keyboard(has_active=False),
        )
        return

    lines = ["🔄 Твои драконы:\n"]
    all_dragons = entries + completed_entries
    for i, ud in enumerate(all_dragons):
        dragon = db.query(Dragon).filter(Dragon.id == ud.dragon_id).first()
        if not dragon:
            continue
        is_current = user.current_dragon_id == ud.dragon_id
        if ud.completed_at:
            pct = 100
            bar = "█" * 10
            status = "⭐"
        else:
            total = dragon.steps_count
            completed = db.query(UserProgress).filter(
                UserProgress.user_id == user.vk_id,
                UserProgress.dragon_id == ud.dragon_id,
                UserProgress.completed == True,
            ).count()
            pct = round((completed / max(total, 1)) * 100) if total else 0
            filled = round((completed / max(total, 1)) * 10) if total else 0
            bar = "█" * filled + "░" * (10 - filled)
            status = "🥚"
        marker = " ← сейчас" if is_current else ""
        label = dragon.name if ud.completed_at else (dragon.egg_type or dragon.name or "?")
        lines.append(f"{i + 1}. {status} {label} {bar} {pct}%{marker}")

    if entries:
        user.state = AWAIT_GARDEN
        db.commit()
        if user.current_dragon_id:
            lines.append("\nНапиши номер дракона, чтобы переключиться, или 0 чтобы не менять.")
        else:
            lines.append("\nНапиши номер дракона, чтобы переключиться на него.")
    else:
        user.state = IDLE
        db.commit()
        if completed_entries:
            lines.append("\nВсе драконы выращены! Добавь нового или загляни в Бестиарий.")

    if user.current_dragon_id:
        from bot.keyboard import await_garden_keyboard
        send_message("\n".join(lines), keyboard=await_garden_keyboard(with_cancel=True))
    else:
        send_message("\n".join(lines))


def cancel_garden(user, db, send_message):
    if not user.current_dragon_id:
        user.state = IDLE
        db.commit()
        send_message(
            "Хорошо, остаёмся без дракона. Нажми «🐉 Добавить дракона» чтобы начать.",
            keyboard=idle_keyboard(has_active=False),
        )
        return

    total = get_total_steps(db, user.current_dragon_id)
    user.state = grow_state(user.current_step)
    db.commit()
    remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
    step_def = get_dragon_step(db, user.current_dragon_id, user.current_step)
    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    label = dragon.egg_type or "яйцо" if dragon else "?"
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(f"🥚 Яйцо «{label}» выращивается.\n⏳ До следующего шага осталось: {hours} ч. {minutes} мин.")
    else:
        msg = f"Остаёмся на «{label}».\n{format_step(step_def, user.current_step, total)}"
        if step_def:
            msg += f"\n\n🎯 Норма: {step_def.crosses_norm} крестиков\nВыбери режим:"
        send_message(msg, keyboard=step_buttons_keyboard())


def switch_dragon(user, num: int, db, send_message):
    active = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id,
        UserDragon.completed_at == "",
    ).all()
    completed_list = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id,
        UserDragon.completed_at != "",
    ).all()

    all_dragons = active + completed_list
    if num < 1 or num > len(all_dragons):
        send_message("❌ Неверный номер. Напиши номер из списка.")
        return

    ud = all_dragons[num - 1]

    if ud.dragon_id == user.current_dragon_id:
        user.state = grow_state(user.current_step)
        db.commit()
        remaining = get_timeout_remaining(db, user.vk_id, ud.dragon_id)
        step_def = get_dragon_step(db, ud.dragon_id, user.current_step)
        dragon = db.query(Dragon).filter(Dragon.id == ud.dragon_id).first()
        label = dragon.egg_type or "яйцо" if dragon else "?"
        if remaining is not None:
            total_secs = int(remaining.total_seconds())
            hours, remainder = divmod(total_secs, 3600)
            minutes = remainder // 60
            send_message(f"🥚 Ты уже выращиваешь «{label}».\n⏳ До следующего шага осталось: {hours} ч. {minutes} мин.")
        else:
            msg = f"Ты уже выращиваешь этого дракона.\n{format_step(step_def, user.current_step, get_total_steps(db, ud.dragon_id))}"
            if step_def:
                msg += f"\n\n🎯 Норма: {step_def.crosses_norm} крестиков\nВыбери режим:"
            send_message(msg, keyboard=step_buttons_keyboard())
        return

    if ud.completed_at:
        dragon = db.query(Dragon).filter(Dragon.id == ud.dragon_id).first()
        name = dragon.name if dragon else "?"
        user.state = IDLE
        db.commit()
        send_message(
            f"⭐ «{name}» уже выращен!\n"
            f"Загляни в мини-приложение, чтобы увидеть его в коллекции, или добавь нового дракона.",
            keyboard=_completed_keyboard(),
        )
        return

    dragon = db.query(Dragon).filter(Dragon.id == ud.dragon_id).first()
    if not dragon:
        send_message("Дракон не найден.")
        return

    completed = db.query(UserProgress).filter(
        UserProgress.user_id == user.vk_id,
        UserProgress.dragon_id == ud.dragon_id,
        UserProgress.completed == True,
    ).count()

    total = dragon.steps_count
    if completed >= total:
        from bot.services.grow_service import complete_dragon
        complete_dragon(db, user.vk_id, ud.dragon_id)
        user.state = IDLE
        user.current_dragon_id = None
        user.current_step = 0
        db.commit()
        send_message(
            f"⭐ «{dragon.name}» уже выращен!\n"
            f"Загляни в мини-приложение, чтобы увидеть его в коллекции, или добавь нового дракона.",
            keyboard=_completed_keyboard(),
        )
        return

    user.current_dragon_id = ud.dragon_id
    user.current_step = completed + 1
    user.state = grow_state(completed + 1)
    db.commit()

    curr_step = completed + 1
    next_def = get_dragon_step(db, ud.dragon_id, curr_step)

    remaining = get_timeout_remaining(db, user.vk_id, ud.dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"▸ Переключился на «{dragon.egg_type or dragon.name or '?'}».\n"
            f"🥚 Яйцо «{dragon.egg_type or '?'}» выращивается.\n"
            f"⏳ Осталось: {hours} ч. {minutes} мин."
        )
    else:
        msg = f"▸ Переключился на «{dragon.egg_type or dragon.name or '?'}».\n{format_step(next_def, curr_step, total)}"
        if next_def:
            msg += f"\n\n🎯 Норма: {next_def.crosses_norm} крестиков\nВыбери режим:"
        send_message(msg, keyboard=step_buttons_keyboard())



def handle_switch_to(user, dragon_id: int, db, send_message):
    from bot.fsm import grow_state, IDLE
    from models import Dragon, UserDragon, UserProgress
    from bot.services.grow_service import get_dragon_step, get_total_steps, get_timeout_remaining
    from bot.handlers.grow import format_step

    ud = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id,
        UserDragon.dragon_id == dragon_id,
    ).first()
    if not ud or ud.completed_at:
        send_message(
            "Этот дракон уже выращен или не найден.\n"
            "Добавь нового дракона или загляни в мини-приложение.",
            keyboard=_completed_keyboard(),
        )
        return

    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon:
        send_message("Дракон не найден.")
        return

    completed = db.query(UserProgress).filter(
        UserProgress.user_id == user.vk_id,
        UserProgress.dragon_id == dragon_id,
        UserProgress.completed == True,
    ).count()
    total = dragon.steps_count
    if completed >= total:
        from bot.services.grow_service import complete_dragon
        complete_dragon(db, user.vk_id, dragon_id)
        if user.current_dragon_id == dragon_id:
            user.current_dragon_id = None
            user.current_step = 0
            user.state = IDLE
            db.commit()
        send_message(
            f"⭐ «{dragon.name}» уже выращен!\n"
            f"Загляни в мини-приложение, чтобы увидеть его в коллекции, или добавь нового дракона.",
            keyboard=_completed_keyboard(),
        )
        return

    next_step = completed + 1
    user.current_dragon_id = dragon_id
    user.current_step = next_step
    user.state = grow_state(next_step)
    db.commit()

    step_def = get_dragon_step(db, dragon_id, next_step)

    remaining = get_timeout_remaining(db, user.vk_id, dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"▸ Переключился на «{dragon.egg_type or dragon.name or '?'}».\n"
            f"🥚 Яйцо «{dragon.egg_type or '?'}» выращивается.\n"
            f"⏳ Осталось: {hours} ч. {minutes} мин."
        )
    else:
        msg = f"▸ Переключился на «{dragon.egg_type or dragon.name or '?'}».\n{format_step(step_def, next_step, total)}"
        if step_def:
            msg += f"\n\n🎯 Норма: {step_def.crosses_norm} крестиков\nВыбери режим:"
        send_message(msg, keyboard=step_buttons_keyboard())


def _completed_keyboard():
    import json
    return json.dumps({
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "🐉 Добавить дракона", "payload": json.dumps({"cmd": "pin"}, ensure_ascii=False)}, "color": "primary"}],
            [
                {"action": {"type": "text", "label": "🔄 Сменить дракона", "payload": json.dumps({"cmd": "garden"}, ensure_ascii=False)}, "color": "secondary"},
                {"action": {"type": "text", "label": "❓ Помощь", "payload": json.dumps({"cmd": "help"}, ensure_ascii=False)}, "color": "secondary"},
            ],
            [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.com/app54663330"}}],
        ],
    }, ensure_ascii=False)
