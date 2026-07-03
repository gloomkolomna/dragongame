"""Command handlers: /start, /help, /status, garden."""

from models import Dragon, UserDragon, UserProgress
from bot.fsm import IDLE, GROW_STEP, AWAIT_GARDEN, step_from_state, grow_state
from bot.services.grow_service import get_total_steps, get_dragon_step
from bot.handlers.grow import format_step


def handle_start(user, db, send_message):
    if user.state == IDLE or not user.current_dragon_id:
        send_message(
            "🐉 Добро пожаловать в Бестиарий драконьих легенд!\n\n"
            "Здесь ты выращиваешь драконов через вышивку.\n"
            "Купил яйцо? Нажми «🐉 Добавить дракона» и введи PIN-код."
        )
    else:
        dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
        name = dragon.name if dragon else "?"
        step = user.current_step
        send_message(
            f"🪴 Ты выращиваешь: {name}\n"
            f"📋 Текущий шаг: {step}\n\n"
            f"Пришли 2 фото (до и после) и напиши «вышито» чтобы продолжить."
        )


def handle_help(send_message):
    send_message(
        "🐉 Добро пожаловать в Бестиарий драконьих легенд!\n\n"
        "📖 Мой Бестиарий — открыть коллекцию в мини-приложении ВК\n"
        "🐉 Добавить дракона — ввести PIN-код с яйца и начать выращивание\n"
        "🔄 Сменить дракона — посмотреть всех драконов и переключиться на другого\n"
        "📋 Статус — узнать текущий шаг и прогресс\n"
        "❓ Помощь — эта справка\n\n"
        "📸 Как проходить шаги:\n"
        "1. Сфотографируй вышивку ДО и ПОСЛЕ\n"
        "2. Отправь оба фото в чат одним сообщением\n"
        "3. В этом же сообщении напиши «вышито»\n\n"
        "🌱 Если передумал менять дракона — напиши «не менять» или нажми кнопку"
    )


def handle_status(user, db, send_message):
    if not user.current_dragon_id:
        send_message("У тебя пока нет активного дракона. Нажми «🐉 Добавить дракона» чтобы начать.")
        return

    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    if not dragon:
        send_message("Дракон не найден.")
        return

    total = get_total_steps(db, user.current_dragon_id)
    current = user.current_step
    pct = round((current / max(total, 1)) * 100) if total else 0
    bar_len = 10
    filled = round((current / max(total, 1)) * bar_len) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    send_message(
        f"🥚 {dragon.name}\n"
        f"📋 Шаг {current} из {total}\n"
        f"{bar} {pct}%"
    )


def handle_garden(user, db, send_message):
    """Show all user dragons with progress, allow switching by number."""

    # Get all active (non-completed) UserDragon entries
    entries = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id,
        UserDragon.completed_at == "",
    ).all()

    # Get completed entries too
    completed_entries = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id,
        UserDragon.completed_at != "",
    ).all()

    if not entries and not completed_entries:
        send_message("🔄 У тебя пока нет драконов. Нажми «🐉 Добавить дракона» чтобы начать.")
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
        lines.append(f"{i + 1}. {status} {dragon.name} {bar} {pct}%{marker}")

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

    if user.current_dragon_id:
        from bot.keyboard import await_garden_keyboard
        send_message("\n".join(lines), keyboard=await_garden_keyboard(with_cancel=True))
    else:
        send_message("\n".join(lines))


def cancel_garden(user, db, send_message):
    """Cancel dragon switching — restore to growing/idle state."""
    if not user.current_dragon_id:
        user.state = IDLE
        db.commit()
        send_message("Хорошо, остаёмся без дракона. Нажми «🐉 Добавить дракона» чтобы начать.")
        return
    
    total = get_total_steps(db, user.current_dragon_id)
    user.state = grow_state(user.current_step)
    db.commit()
    step_def = get_dragon_step(db, user.current_dragon_id, user.current_step)
    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    name = dragon.name if dragon else "?"
    send_message(f"Остаёмся на «{name}».\n{format_step(step_def, user.current_step, total)}\n\nПришли фото и напиши «вышито» когда выполнишь.")


def switch_dragon(user, num: int, db, send_message):
    """Switch active dragon by garden list number."""
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
        step_def = get_dragon_step(db, ud.dragon_id, user.current_step)
        msg = f"Ты уже выращиваешь этого дракона.\n{format_step(step_def, user.current_step, get_total_steps(db, ud.dragon_id))}"
        msg += "\n\nПришли 2 фото и напиши «вышито» когда выполнишь."
        send_message(msg)
        return

    if ud.completed_at:
        dragon = db.query(Dragon).filter(Dragon.id == ud.dragon_id).first()
        send_message(f"⭐ {dragon.name if dragon else '?'} уже выращен! Можешь посмотреть его в мини-приложении.")
        user.state = IDLE
        db.commit()
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
        send_message(f"⭐ {dragon.name} уже выращен! Можешь посмотреть его в мини-приложении.")
        user.state = IDLE
        user.current_dragon_id = None
        user.current_step = 0
        db.commit()
        return

    user.current_dragon_id = ud.dragon_id
    user.current_step = completed + 1
    user.state = grow_state(completed + 1)
    db.commit()

    curr_step = completed + 1
    next_def = get_dragon_step(db, ud.dragon_id, curr_step)

    msg = f"▸ Переключился на «{dragon.name}».\n{format_step(next_def, curr_step, total)}"
    msg += "\n\nПришли фото и напиши «вышито» когда выполнишь."

    send_message(msg)
