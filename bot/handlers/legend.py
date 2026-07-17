"""Legend handler — rarity-3 post-hatch legend fragments (phase=1)."""

import json
import os
import re
from bot.fsm import IDLE, legend_state, legend_fragment_from_state, is_legend_waiting, state_mode
from bot.services.legend_service import (
    get_legend_steps, get_legend_total, get_next_legend_fragment,
    complete_legend_fragment,
)
from bot.services.grow_service import credit_stitches, is_suspicious, is_blocked, create_suspicious_report, notify_admin
from bot.keyboard import legend_buttons_keyboard, legend_next_keyboard, idle_keyboard

_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")


def _legend_dragon_id(user):
    try:
        data = json.loads(user.state_data or "{}")
        return data.get("legend_dragon_id")
    except (json.JSONDecodeError, TypeError):
        return None


def _set_legend_dragon_id(user, dragon_id):
    try:
        data = json.loads(user.state_data or "{}")
    except (json.JSONDecodeError, TypeError):
        data = {}
    data["legend_dragon_id"] = dragon_id
    user.state_data = json.dumps(data, ensure_ascii=False)


def _clear_legend(user):
    try:
        data = json.loads(user.state_data or "{}")
    except (json.JSONDecodeError, TypeError):
        data = {}
    data.pop("legend_dragon_id", None)
    user.state_data = json.dumps(data, ensure_ascii=False)


def _attach(upload_image, image_path, vk_id):
    if not upload_image or not image_path:
        return ""
    filepath = os.path.join(_IMAGES, os.path.basename(image_path))
    if not os.path.isfile(filepath):
        return ""
    from bot.services.grow_service import log_to_db

    def _log_err(msg, tb=""):
        from db import SessionLocal
        _db = SessionLocal()
        try:
            log_to_db("bot", "UPLOAD", f"{msg} (file={filepath})", tb, vk_id, _db)
        finally:
            _db.close()

    return upload_image(filepath, peer_id=vk_id, log_error=_log_err)


def _legend_cover_attach(upload_image, dragon, vk_id):
    path = getattr(dragon, "legend_image_path", "") or ""
    return _attach(upload_image, path, vk_id)


def _show_fragment(user, dragon, frag, total, db, send_message, upload_image):
    user.state = legend_state(frag.step_number)
    _set_legend_dragon_id(user, dragon.id)
    db.commit()
    msg = (
        f"📖 Легенда дракона «{dragon.name}» — отрывок {frag.step_number} из {total}\n"
    )
    task = frag.magic_action or frag.task_description or ""
    if task:
        msg += f"\n📋 Задание: {task}\n"
    msg += f"\n🎯 Норма стежков: {frag.crosses_norm}\nВыбери режим:"
    attachment = _legend_cover_attach(upload_image, dragon, user.vk_id)
    send_message(msg, attachment=attachment, keyboard=legend_buttons_keyboard())


def handle_legend_start(user, dragon_id, db, send_message, upload_image=None):
    from models import Dragon, UserDragon
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon or dragon.rarity != 3:
        send_message("У этого дракона нет легенды.")
        return
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == user.vk_id, UserDragon.dragon_id == dragon_id
    ).first()
    if not ud or not ud.completed_at:
        send_message("Сначала нужно вырастить этого дракона.")
        return
    total = get_legend_total(db, dragon_id)
    if total == 0:
        send_message("Легенда этого дракона ещё не написана.")
        return
    frag = get_next_legend_fragment(db, user.vk_id, dragon_id)
    if not frag:
        send_message(f"📖 Легенда дракона «{dragon.name}» уже рассказана полностью.")
        return
    _show_fragment(user, dragon, frag, total, db, send_message, upload_image)


def handle_legend_mode(user, mode, db, send_message):
    from models import Dragon
    dragon_id = _legend_dragon_id(user)
    frag_num = legend_fragment_from_state(user.state)
    if not dragon_id or not frag_num:
        send_message("Легенда не активна. Открой её из карточки дракона.")
        return
    from bot.services.legend_service import get_legend_steps
    step_def = next((s for s in get_legend_steps(db, dragon_id) if s.step_number == frag_num), None)
    norm = step_def.crosses_norm if step_def else 1000
    required = norm * 2 if mode == "x2" else norm
    user.state = legend_state(frag_num, mode)
    db.commit()
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    label = "⚠ Режим «Штраф (x2)»" if mode == "x2" else "✅ Режим «Норма»"
    attachment = _legend_cover_attach(None, dragon, user.vk_id) if dragon else ""
    send_message(
        f"{label} — нужно вышить не менее {required} стежков.\n"
        f"Отправь одним сообщением фото работы и текст: «вышито {required}».",
        attachment=attachment,
    )


def handle_legend_message(user, text, attachments, db, send_message, upload_image=None):
    if not is_legend_waiting(user.state):
        return True
    from models import Dragon
    dragon_id = _legend_dragon_id(user)
    if not dragon_id:
        user.state = IDLE
        db.commit()
        send_message("Легенда не активна.")
        return True

    mode = state_mode(user.state)
    frag_num = legend_fragment_from_state(user.state)
    step_def = next((s for s in get_legend_steps(db, dragon_id) if s.step_number == frag_num), None)
    base_norm = step_def.crosses_norm if step_def else 1000
    required = base_norm * 2 if mode == "x2" else base_norm

    if "вышито" not in text.lower():
        send_message('Пожалуйста, отправьте сообщение в формате: «вышито [число]»')
        return True
    numbers = re.findall(r"\d+", text)
    if not numbers:
        send_message('Пожалуйста, отправьте сообщение в формате: «вышито [число]»')
        return True
    crosses = int(numbers[0])
    if crosses < required:
        send_message(
            f"❌ Вы вышили {crosses} стежков, а нужно не менее {required}.\n"
            f"Вышивайте дальше и отправьте повторно фото и «вышито [число]»."
        )
        return True

    photo_infos = [a["photo"] for a in attachments if a.get("type") == "photo" and a.get("photo")]
    if len(photo_infos) == 0:
        send_message("❌ Прикрепи фото работы вместе с текстом «вышито [число]».")
        return True

    def fmt_photo(p):
        return f"photo{p['owner_id']}_{p['id']}"

    photo_before_id = fmt_photo(photo_infos[0])
    photo_after_id = fmt_photo(photo_infos[1]) if len(photo_infos) > 1 else ""

    if is_blocked(crosses, required):
        create_suspicious_report(
            db, user.vk_id, dragon_id, frag_num, crosses, required, mode,
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
            raw_message=text,
        )
        send_message(
            f"⚠ Ты заявил {crosses} стежков при норме {required} — это слишком много.\n"
            "Отрывок не засчитан. Отправь, пожалуйста, корректное число."
        )
        db.commit()
        return True

    credit_stitches(db, user.vk_id, crosses)

    if is_suspicious(crosses, required):
        create_suspicious_report(
            db, user.vk_id, dragon_id, frag_num, crosses, required, mode,
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
            raw_message=text,
        )
        send_message(
            "⚠ Твой отчёт кажется подозрительным и отправлен на проверку. "
            "Стежки зачислены, но администратор может скорректировать баланс."
        )
        notify_admin(
            f"⚠ Подозрительный отчёт (легенда) от id{user.vk_id}\n"
            f"Дракон #{dragon_id}, отрывок {frag_num}, режим {mode}\n"
            f"Заявлено: {crosses}, норма: {required}\n"
            f"https://vk.ru/gim239999455/convo/{user.vk_id}"
        )

    complete_legend_fragment(
        db, user.vk_id, dragon_id, frag_num,
        photo_before_id=photo_before_id, photo_after_id=photo_after_id,
    )

    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    total = get_legend_total(db, dragon_id)
    next_frag = get_next_legend_fragment(db, user.vk_id, dragon_id)

    # Show the fragment text after successful completion
    if step_def and step_def.task_description:
        frag_text = f"📖 Отрывок {frag_num}:\n\n{step_def.task_description}"
        attachment = _legend_cover_attach(upload_image, dragon, user.vk_id) if dragon else ""
        send_message(frag_text, attachment=attachment)

    if next_frag is None:
        user.state = IDLE
        _clear_legend(user)
        db.commit()
        msg = (
            f"📖✨ Легенда дракона «{dragon.name if dragon else '?'}» рассказана полностью!\n\n"
            f"📖 Легенда добавлена в Библиотеку легенд в мини-приложении."
        )
        send_message(msg, keyboard=idle_keyboard(has_active=bool(user.current_dragon_id)))
        return True

    user.state = legend_state(frag_num)
    db.commit()
    send_message(
        f"📖 Отрывок {frag_num} прочитан. Хочешь продолжить?",
        keyboard=legend_next_keyboard(),
    )
    return True


def handle_legend_next(user, db, send_message, upload_image=None):
    dragon_id = _legend_dragon_id(user)
    if not dragon_id:
        send_message("Легенда не активна.")
        return
    from models import Dragon
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon:
        send_message("Дракон не найден.")
        return
    next_frag = get_next_legend_fragment(db, user.vk_id, dragon_id)
    if not next_frag:
        user.state = IDLE
        _clear_legend(user)
        db.commit()
        msg = (
            f"📖✨ Легенда дракона «{dragon.name}» рассказана полностью!\n\n"
            f"📖 Легенда добавлена в Библиотеку легенд в мини-приложении."
        )
        send_message(msg, keyboard=idle_keyboard(has_active=bool(user.current_dragon_id)))
        return
    total = get_legend_total(db, dragon_id)
    _show_fragment(user, dragon, next_frag, total, db, send_message, upload_image)
