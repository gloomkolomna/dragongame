"""Epic dragon handler — egg growth, hatch, naming, daily care."""

import os
from bot.fsm import (
    IDLE, AWAIT_EPIC_NAME, AWAIT_EPIC_RESTART, AWAIT_EPICS,
    epic_egg_state, epic_egg_step_from_state, is_epic_egg_waiting,
    epic_care_state, state_mode, is_growing, grow_state,
)
from bot.services.grow_service import (
    get_dragon_step, get_total_steps, complete_step,
    credit_stitches, is_suspicious, is_blocked, create_suspicious_report, notify_admin,
)
from bot.keyboard import epic_egg_buttons_keyboard, idle_keyboard, empty_keyboard

_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")


def _attach(upload_image, image_path, vk_id):
    if not upload_image or not image_path:
        return ""
    filepath = os.path.join(_IMAGES, os.path.basename(image_path))
    if not os.path.isfile(filepath):
        return ""
    from datetime import datetime
    from bot.services.grow_service import log_to_db

    def _log_err(msg, tb=""):
        from db import SessionLocal
        _db = SessionLocal()
        try:
            log_to_db("bot", "UPLOAD", f"{msg} (file={filepath})", tb, vk_id, _db)
        finally:
            _db.close()

    return upload_image(filepath, peer_id=vk_id, log_error=_log_err)


def _extract_crosses(text):
    import re
    if "вышито" not in text.lower():
        return None
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else None


def _photos(attachments):
    return [a["photo"] for a in attachments if a.get("type") == "photo" and a.get("photo")]


def _fmt_photo(p):
    return f"photo{p['owner_id']}_{p['id']}"


def send_epic_spawn_notice(epic, user, db, send_message, upload_image=None):
    import json as j
    epic_kb = j.dumps({
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "🐲 Растить эпического", "payload": j.dumps({"cmd": "epic"}, ensure_ascii=False)}, "color": "primary"}],
            [{"action": {"type": "text", "label": "📖 Список Бестиария", "payload": j.dumps({"cmd": "garden"}, ensure_ascii=False)}, "color": "secondary"}],
            [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.ru/app54663330"}}],
        ],
    }, ensure_ascii=False)
    attachment = _attach(upload_image, epic.egg_path, user.vk_id)
    send_message(
        "🌙 Кто-то подкинул тебе под дверь ещё одно яйцо... оно кажется необычным.\n"
        "🐲 Это эпический дракон! Нажми «🐲 Растить эпического», чтобы начать заботиться о нём.",
        attachment=attachment, keyboard=epic_kb,
    )


def maybe_offer_epic(user, db, send_message, upload_image=None):
    """Lazy, idempotent first-epic spawn — fires on any interaction after the first
    regular dragon is completed, covering grow/scheduler/admin completion paths."""
    from services.epic_service import maybe_spawn_first_epic
    if user.epic_unlocked and user.epic_dragon_id:
        return
    epic = maybe_spawn_first_epic(db, user.vk_id)
    if epic:
        send_epic_spawn_notice(epic, user, db, send_message, upload_image)


# ─── Entry ───

def handle_epic_command(user, db, send_message, upload_image=None):
    from services.epic_service import get_epic_dragon, is_egg_hatched, get_care
    import json
    dragon = get_epic_dragon(db, user.vk_id)
    if not dragon:
        send_message(
            "🐲 Эпического дракона пока нет. Он появится, когда ты вырастишь своего первого дракона."
        )
        return
    care = get_care(db, user.vk_id)
    if care:
        from bot.handlers.epic_care import show_care_action
        show_care_action(user, db, send_message, upload_image)
        return
    if is_egg_hatched(db, user.vk_id):
        _prompt_name(user, dragon, db, send_message)
        return
    sd = json.loads(user.state_data or "{}")
    if sd.pop("_needs_egg_intro", None):
        user.state_data = json.dumps(sd, ensure_ascii=False)
        user.state = "await_epic_egg_intro"
        db.commit()
        from bot.keyboard import epic_egg_intro_keyboard
        send_message(
            f"🥚 Перед тобой новое эпическое яйцо — «{dragon.egg_type or dragon.name}».\n"
            "🌟 Нажми «Бережно принять яйцо», чтобы начать выращивание!",
            keyboard=epic_egg_intro_keyboard(),
        )
        return
    _show_egg_step(user, dragon, db, send_message, upload_image)


def grown_epics(db, vk_id):
    from models import Dragon, UserDragon, UserProgress
    rows = (
        db.query(Dragon)
        .join(UserDragon, UserDragon.dragon_id == Dragon.id)
        .filter(UserDragon.user_id == vk_id, Dragon.is_epic == True)
        .order_by(UserDragon.id)
        .all()
    )
    result = []
    for d in rows:
        total = d.steps_count or 0
        if total <= 0:
            continue
        done = db.query(UserProgress).filter(
            UserProgress.user_id == vk_id,
            UserProgress.dragon_id == d.id,
            UserProgress.step_number > 0,
            UserProgress.completed == True,
        ).count()
        if done >= total:
            result.append(d)
    return result


def user_has_epic(db, vk_id):
    from services.epic_service import all_user_epics
    return len(all_user_epics(db, vk_id)) > 0


def handle_epics(user, db, send_message):
    from services.epic_service import get_epic_name_for, all_user_epics, egg_completed_count, is_egg_hatched, get_care
    dragons = all_user_epics(db, user.vk_id)
    if not dragons:
        send_message(
            "🐉 У тебя пока нет активных эпических драконов.\n"
            "Первый появится после выращивания любого обычного дракона."
        )
        return
    lines = ["🐉 Эпические драконы — выбери, к кому перейти:\n"]
    for i, d in enumerate(dragons, start=1):
        name = get_epic_name_for(db, user.vk_id, d.id) or d.egg_type or d.name or "?"
        marker = " 👈 сейчас" if user.epic_dragon_id == d.id else ""
        hatched = is_egg_hatched_for(db, user.vk_id, d.id)
        if hatched:
            lines.append(f"{i}. 🐲 {name}{marker}")
        else:
            egg_done = egg_completed_count_for(db, user.vk_id, d.id)
            total = d.steps_count or 0
            lines.append(f"{i}. 🥚 {name} ({egg_done}/{total}){marker}")
    lines.append("\nНапиши номер, чтобы перейти к дракону, или «0», чтобы вернуться.")
    user.state = AWAIT_EPICS
    db.commit()
    send_message("\n".join(lines))


def is_egg_hatched_for(db, vk_id, dragon_id):
    from models import Dragon, UserProgress
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon or not dragon.steps_count:
        return False
    done = db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == dragon_id,
        UserProgress.step_number > 0,
        UserProgress.completed == True,
    ).count()
    return done >= dragon.steps_count


def egg_completed_count_for(db, vk_id, dragon_id):
    from models import UserProgress
    return db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == dragon_id,
        UserProgress.step_number > 0,
        UserProgress.completed == True,
    ).count()


def handle_epics_pick(user, num, db, send_message, upload_image=None):
    from services.epic_service import all_user_epics
    dragons = all_user_epics(db, user.vk_id)
    if num < 1 or num > len(dragons):
        send_message("❌ Неверный номер. Напиши номер из списка.")
        return
    dragon = dragons[num - 1]
    user.epic_dragon_id = dragon.id
    db.commit()
    handle_epic_command(user, db, send_message, upload_image)


def cancel_epics(user, db, send_message):
    if user.current_dragon_id:
        user.state = grow_state(user.current_step)
    else:
        user.state = IDLE
    db.commit()
    send_message("Хорошо, вернулись.")


def _show_egg_step(user, dragon, db, send_message, upload_image):
    from services.epic_service import egg_completed_count
    total = get_total_steps(db, dragon.id)
    step = egg_completed_count(db, user.vk_id) + 1
    step_def = get_dragon_step(db, dragon.id, step)
    user.state = epic_egg_state(step)
    db.commit()
    msg = f"🐲🥚 Эпическое яйцо «{dragon.egg_type or dragon.name}» — шаг {step} из {total}\n"
    if step_def and step_def.task_description:
        msg += f"\n{step_def.task_description}\n"
    norm = step_def.crosses_norm if step_def else 1000
    msg += f"\n🎯 Норма крестиков: {norm}\nВыбери режим:"
    attachment = _attach(upload_image, dragon.egg_path, user.vk_id)
    send_message(msg, attachment=attachment, keyboard=epic_egg_buttons_keyboard())


def handle_epic_egg_mode(user, mode, db, send_message):
    from services.epic_service import get_epic_dragon
    dragon = get_epic_dragon(db, user.vk_id)
    step = epic_egg_step_from_state(user.state)
    if not dragon or not step:
        send_message("Эпическое яйцо не активно.")
        return
    step_def = get_dragon_step(db, dragon.id, step)
    norm = step_def.crosses_norm if step_def else 1000
    required = norm * 2 if mode == "x2" else norm
    user.state = epic_egg_state(step, mode)
    db.commit()
    label = "⚠ Режим «Штраф (x2)»" if mode == "x2" else "✅ Режим «Норма»"
    send_message(
        f"{label} — нужно вышить не менее {required} крестиков.\n"
        f"Отправь одним сообщением фото работы и текст: «вышито {required}»."
    )


def handle_epic_egg_message(user, text, attachments, db, send_message, upload_image=None):
    from services.epic_service import get_epic_dragon, egg_completed_count, is_egg_hatched
    dragon = get_epic_dragon(db, user.vk_id)
    if not dragon:
        user.state = IDLE
        db.commit()
        send_message("Эпическое яйцо не активно.")
        return True

    mode = state_mode(user.state)
    step = epic_egg_step_from_state(user.state)
    step_def = get_dragon_step(db, dragon.id, step)
    base_norm = step_def.crosses_norm if step_def else 1000
    required = base_norm * 2 if mode == "x2" else base_norm

    crosses = _extract_crosses(text)
    if crosses is None:
        send_message('Пожалуйста, отправьте сообщение в формате: «вышито [число]»')
        return True
    if crosses < required:
        send_message(
            f"❌ Вы вышили {crosses} крестиков, а нужно не менее {required}.\n"
            f"Вышивайте дальше и отправьте повторно фото и «вышито [число]»."
        )
        return True

    photos = _photos(attachments)
    if not photos:
        send_message("❌ Прикрепи фото работы вместе с текстом «вышито [число]».")
        return True

    photo_before_id = _fmt_photo(photos[0])
    photo_after_id = _fmt_photo(photos[1]) if len(photos) > 1 else ""

    if is_blocked(crosses, required):
        create_suspicious_report(
            db, user.vk_id, dragon.id, step, crosses, required, mode,
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
            raw_message=text,
        )
        send_message(
            f"⚠ Ты заявил {crosses} крестиков при норме {required} — это слишком много.\n"
            "Шаг не засчитан. Отправь, пожалуйста, корректное число."
        )
        db.commit()
        return True

    credit_stitches(db, user.vk_id, crosses)
    if is_suspicious(crosses, required):
        create_suspicious_report(
            db, user.vk_id, dragon.id, step, crosses, required, mode,
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
            raw_message=text,
        )
        send_message(
            "⚠ Твой отчёт кажется подозрительным и отправлен на проверку. "
            "Крестики зачислены, но администратор может скорректировать баланс."
        )
        notify_admin(
            f"⚠ Подозрительный отчёт (эпическое яйцо) от id{user.vk_id}\n"
            f"Дракон #{dragon.id}, шаг {step}, режим {mode}\n"
            f"Заявлено: {crosses}, норма: {required}\n"
            f"https://vk.ru/gim239999455/convo/{user.vk_id}"
        )

    complete_step(db, user.vk_id, dragon.id, step,
                  photo_before_id=photo_before_id, photo_after_id=photo_after_id)

    if is_egg_hatched(db, user.vk_id):
        _prompt_name(user, dragon, db, send_message)
    else:
        send_message(f"✅ Шаг {step} эпического яйца выполнен!")
        _show_egg_step(user, dragon, db, send_message, upload_image)
    return True


def _prompt_name(user, dragon, db, send_message):
    user.state = AWAIT_EPIC_NAME
    db.commit()
    from bot.keyboard import epic_name_keyboard
    send_message(
        "🐲 Твой эпический дракон вылупился!\n"
        "Как ты его назовёшь? Напиши имя одним сообщением.",
        keyboard=epic_name_keyboard(),
    )


def handle_epic_name(user, text, db, send_message, upload_image=None):
    from services.epic_service import set_epic_name, start_care, get_epic_dragon
    name = (text or "").strip()[:50]
    if not name:
        send_message("Пожалуйста, напиши имя дракона одним сообщением.")
        return True
    set_epic_name(db, user.vk_id, name)
    care = start_care(db, user.vk_id)
    dragon = get_epic_dragon(db, user.vk_id)

    hatch_msg = f"🎉🐲 Знакомься, «{name}» вылупился!\n"
    hatch_msg += "✨ Редкость: Эпический 🐲\n"
    if dragon and dragon.description:
        hatch_msg += f"\n{dragon.description}\n"
    dragon_attachment = _attach(upload_image, dragon.dragon_path if dragon else "", user.vk_id)
    send_message(hatch_msg, attachment=dragon_attachment)

    if not care:
        user.state = IDLE
        db.commit()
        send_message(
            f"🐲 «{name}» вылупился! Стадии ухода ещё не настроены — загляни позже.",
            keyboard=idle_keyboard(has_active=bool(user.current_dragon_id)),
        )
        return True
    user.state = epic_care_state(care.stage_id)
    db.commit()
    send_message(f"🐲 «{name}» подрастает! Начинается забота о малыше.")
    from bot.handlers.epic_care import show_care_action
    show_care_action(user, db, send_message, upload_image)
    return True
