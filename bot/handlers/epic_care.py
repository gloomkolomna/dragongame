"""Epic care handler — daily care cycle actions (Phase 5) + finale (Phase 6)."""

import os
import re
from bot.fsm import IDLE, AWAIT_EPIC_RESTART, epic_care_state, epic_care_sub_state, state_mode, is_epic_care_sub, is_epic_care_sub_waiting
from bot.services.grow_service import (
    credit_stitches, is_suspicious, create_suspicious_report, notify_admin,
)
from bot.keyboard import epic_care_keyboard, epic_care_item_keyboard, epic_care_optional_item_keyboard, idle_keyboard, sub_step_keyboard

_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")


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


def _fmt_remaining(remaining):
    total = int(remaining.total_seconds())
    h, rem = divmod(total, 3600)
    m = rem // 60
    return f"{h} ч. {m} мин."


def show_care_action(user, db, send_message, upload_image=None):
    from services.epic_service import (
        get_care, get_epic_dragon, get_epic_name, get_stage,
        get_current_action, get_care_remaining, missing_action_items,
        has_action_items, action_items,
    )
    care = get_care(db, user.vk_id)
    dragon = get_epic_dragon(db, user.vk_id)
    if not care or not dragon:
        send_message("🐲 Эпический дракон не найден.")
        return
    name = get_epic_name(db, user.vk_id) or dragon.name
    stage = get_stage(db, care.stage_id)

    remaining = get_care_remaining(db, care)
    if remaining is not None:
        send_message(
            f"😴 «{name}» отдыхает после заботы.\n⏳ Вернись через {_fmt_remaining(remaining)}."
        )
        return

    action = get_current_action(db, care)
    if not action:
        send_message(f"🐲 «{name}»: на стадии «{stage.name if stage else '?'}» нет действий ухода.")
        return

    if getattr(action, "action_type", "simple") == "composite":
        _show_composite_action(user, db, send_message, upload_image, care, action, dragon, name, stage)
        return

    from services.epic_service import has_non_optional_items, missing_optional_action_items

    has_items = has_action_items(db, action.id)
    missing_non_opt = missing_action_items(db, user.vk_id, action.id) if has_items else []
    only_optional = has_items and not has_non_optional_items(db, action.id)

    cycle_no = (care.cycles_completed or 0) + 1
    total_cycles = stage.cycles_count if stage else 1
    base_msg = (
        f"🐲 «{name}» — стадия «{stage.name if stage else '?'}» (цикл {cycle_no}/{total_cycles})\n"
        f"\n▶ {action.action_label}\n"
    )
    if action.hint:
        base_msg += f"💡 {action.hint}\n"

    if has_items:
        if missing_non_opt:
            names = ", ".join(f"«{m.name}»" for m in missing_non_opt)
            from bot.keyboard import _keyboard, row, bestiary_link_row
            kb = _keyboard([row(("🛒 Магазин", "shop")), bestiary_link_row()])
            send_message(
                f"🐲 «{name}» — стадия «{stage.name if stage else '?'}»\n"
                f"Для действия «{action.action_label}» нужно купить в магазине: {names}.",
                keyboard=kb,
            )
            return

        user.state = epic_care_state(care.stage_id)
        db.commit()
        item_names = ", ".join(it.name for it in action_items(db, action.id))
        item_names_parts = []
        for it in action_items(db, action.id):
            if it.is_optional:
                item_names_parts.append(f"{it.name} (необяз.)")
            else:
                item_names_parts.append(it.name)
        item_names = ", ".join(item_names_parts)
        msg = base_msg + f"\n📦 Товары: {item_names}\n"
        if only_optional:
            msg += "Нажми «🎒 Использовать», если есть товары, или «⏭ Пропустить»."
            kb = epic_care_optional_item_keyboard()
        else:
            msg += "Нажми «🎒 Использовать», чтобы применить."
            kb = epic_care_item_keyboard()
        action_img = getattr(action, "image_path", "") or ""
        attachment = _attach(upload_image, action_img or (stage.image_start if stage else ""), user.vk_id)
        send_message(msg, attachment=attachment, keyboard=kb)
    else:
        user.state = epic_care_state(care.stage_id)
        db.commit()
        msg = base_msg
        if action.task:
            msg += f"📝 {action.task}\n"
        msg += f"\n🎯 Норма крестиков: {action.crosses_norm}\nВыбери режим:"
        action_img = getattr(action, "image_path", "") or ""
        attachment = _attach(upload_image, action_img or (stage.image_start if stage else ""), user.vk_id)
        send_message(msg, attachment=attachment, keyboard=epic_care_keyboard())


def handle_care_use_item(user, db, send_message, upload_image=None):
    from services.epic_service import (
        get_care, get_current_action, get_epic_name,
        get_epic_dragon, missing_action_items, consume_owned_action_items,
        has_action_items, advance_care, has_non_optional_items,
    )
    care = get_care(db, user.vk_id)
    action = get_current_action(db, care)
    if not care or not action:
        user.state = IDLE
        db.commit()
        send_message("Уход не активен.")
        return

    if not has_action_items(db, action.id):
        send_message("Для этого действия не нужны товары. Используй «🎯 Норма» или «⚡ Штраф (x2)».")
        return

    missing = missing_action_items(db, user.vk_id, action.id)
    if missing:
        names = ", ".join(f"«{m.name}»" for m in missing)
        from bot.keyboard import _keyboard, row, bestiary_link_row
        kb = _keyboard([row(("🛒 Магазин", "shop")), bestiary_link_row()])
        send_message(
            f"❌ У тебя нет {names}. Купи их в магазине!",
            keyboard=kb,
        )
        return

    from services.epic_service import get_epic_dragon
    epic_dragon = get_epic_dragon(db, user.vk_id)
    name = get_epic_name(db, user.vk_id) or (epic_dragon.name if epic_dragon else "малыш")

    consume_owned_action_items(db, user.vk_id, action.id)

    _award_action_moodlet(db, user.vk_id, care, action)
    send_message(f"✅ «{action.action_label}» — {name} доволен! Товары использованы.")

    event = advance_care(db, care)
    kind = event.get("event")

    if kind == "finale":
        _finale(user, db, send_message, upload_image, event)
        return

    if kind == "stage_up":
        nxt = event["stage"]
        send_message(f"🌟 «{name}» перешёл на новую стадию: «{nxt.name}»!")

    show_care_action(user, db, send_message, upload_image)


def handle_care_skip_item(user, db, send_message, upload_image=None):
    from services.epic_service import (
        get_care, get_current_action, get_epic_name,
        get_epic_dragon, advance_care, has_non_optional_items,
    )
    care = get_care(db, user.vk_id)
    action = get_current_action(db, care)
    if not care or not action:
        user.state = IDLE
        db.commit()
        send_message("Уход не активен.")
        return

    if has_non_optional_items(db, action.id):
        send_message("В этом действии есть обязательные товары. Сначала купи их.")
        return

    from services.epic_service import get_epic_dragon
    epic_dragon = get_epic_dragon(db, user.vk_id)
    name = get_epic_name(db, user.vk_id) or (epic_dragon.name if epic_dragon else "малыш")

    _award_action_moodlet(db, user.vk_id, care, action)
    send_message(f"✅ «{action.action_label}» пропущено. «{name}» не против.")

    event = advance_care(db, care)
    kind = event.get("event")

    if kind == "finale":
        _finale(user, db, send_message, upload_image, event)
        return

    if kind == "stage_up":
        nxt = event["stage"]
        send_message(f"🌟 «{name}» перешёл на новую стадию: «{nxt.name}»!")

    show_care_action(user, db, send_message, upload_image)


def handle_care_mode(user, mode, db, send_message):
    from services.epic_service import get_care, get_current_action
    care = get_care(db, user.vk_id)
    action = get_current_action(db, care)
    if not care or not action:
        send_message("Уход не активен.")
        return
    norm = action.crosses_norm or 1000
    required = norm * 2 if mode == "x2" else norm
    user.state = epic_care_state(care.stage_id, mode)
    db.commit()
    label = "⚠ Режим «Штраф (x2)»" if mode == "x2" else "✅ Режим «Норма»"
    send_message(
        f"{label} — нужно вышить не менее {required} крестиков.\n"
        f"Отправь одним сообщением фото работы и текст: «вышито {required}»."
    )


def handle_care_message(user, text, attachments, db, send_message, upload_image=None):
    from services.epic_service import get_care, get_current_action, advance_care, get_epic_name
    care = get_care(db, user.vk_id)
    action = get_current_action(db, care)
    if not care or not action:
        user.state = IDLE
        db.commit()
        send_message("Уход не активен.")
        return True

    mode = state_mode(user.state)
    base_norm = action.crosses_norm or 1000
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
            f"❌ Вы вышили {crosses} крестиков, а нужно не менее {required}.\n"
            f"Вышивайте дальше и отправьте повторно фото и «вышито [число]»."
        )
        return True

    photos = [a["photo"] for a in attachments if a.get("type") == "photo" and a.get("photo")]
    if not photos:
        send_message("❌ Прикрепи фото работы вместе с текстом «вышито [число]».")
        return True

    def fmt_photo(p):
        return f"photo{p['owner_id']}_{p['id']}"

    photo_before_id = fmt_photo(photos[0])
    photo_after_id = fmt_photo(photos[1]) if len(photos) > 1 else ""
    from services.epic_service import get_epic_dragon
    epic_dragon = get_epic_dragon(db, user.vk_id)

    credit_stitches(db, user.vk_id, crosses)
    if is_suspicious(crosses, required):
        create_suspicious_report(
            db, user.vk_id, epic_dragon.id if epic_dragon else None,
            action.order_in_cycle, crosses, required, mode,
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
            raw_message=text,
        )
        send_message(
            "⚠ Твой отчёт кажется подозрительным и отправлен на проверку. "
            "Крестики зачислены, но администратор может скорректировать баланс."
        )
        notify_admin(
            f"⚠ Подозрительный отчёт (уход) от id{user.vk_id}\n"
            f"Действие «{action.action_label}», режим {mode}\n"
            f"Заявлено: {crosses}, норма: {required}\n"
            f"https://vk.com/gim239999455/convo/{user.vk_id}"
        )

    _award_action_moodlet(db, user.vk_id, care, action)

    name = get_epic_name(db, user.vk_id) or (epic_dragon.name if epic_dragon else "малыш")
    send_message(f"✅ «{action.action_label}» — сделано! «{name}» доволен.")

    event = advance_care(db, care)
    kind = event.get("event")

    if kind == "finale":
        _finale(user, db, send_message, upload_image, event)
        return True

    if kind == "stage_up":
        nxt = event["stage"]
        send_message(f"🌟 «{name}» перешёл на новую стадию: «{nxt.name}»!")

    show_care_action(user, db, send_message, upload_image)
    return True


# ─── Composite action handlers ───

def _show_composite_action(user, db, send_message, upload_image, care, action, dragon, name, stage):
    from services.epic_service import get_sub_actions, get_current_sub_step, get_sub_steps
    from bot.keyboard import sub_action_keyboard, sub_step_keyboard

    if care.current_sub_action_id:
        sub_step = get_current_sub_step(db, care)
        if sub_step:
            user.state = epic_care_sub_state(care.stage_id)
            db.commit()
            msg = f"🐲 «{name}» — «{action.action_label}»\n📝 {sub_step.task or sub_step.step_label}"
            if sub_step.hint:
                msg += f"\n💡 {sub_step.hint}"
            msg += f"\n\n🎯 Норма крестиков: {sub_step.crosses_norm or 1000}\nВыбери режим:"
            action_img = getattr(sub_step, "image_path", "") or ""
            attachment = _attach(upload_image, action_img, user.vk_id)
            send_message(msg, attachment=attachment, keyboard=sub_step_keyboard())
            return

    sub_actions = get_sub_actions(db, action.id)
    if not sub_actions:
        send_message(f"🐲 «{name}»: у действия «{action.action_label}» нет вариантов.")
        return

    from services.epic_service import missing_sub_items
    missing_map = {}
    for sa in sub_actions:
        missing = missing_sub_items(db, user.vk_id, sa.id)
        if missing:
            missing_map[sa.id] = missing

    msg = f"🐲 «{name}» — «{action.action_label}»\nВыбери вариант:"
    if action.image_path:
        attachment = _attach(upload_image, action.image_path, user.vk_id)
        send_message(msg, attachment=attachment, keyboard=sub_action_keyboard(sub_actions, missing_map))
    else:
        send_message(msg, keyboard=sub_action_keyboard(sub_actions, missing_map))


def handle_choose_sub(user, sub_id, db, send_message, upload_image=None):
    from services.epic_service import (
        get_care, get_sub_action, start_sub_action,
        get_current_sub_step, get_sub_steps, missing_sub_items,
        get_epic_dragon, get_epic_name, get_stage,
    )
    care = get_care(db, user.vk_id)
    if not care:
        send_message("Уход не активен.")
        return

    sub_action = get_sub_action(db, sub_id)
    if not sub_action:
        send_message("Вариант не найден.")
        return

    missing = missing_sub_items(db, user.vk_id, sub_id)
    if missing:
        names = ", ".join(f"«{m.name}»" for m in missing)
        from bot.keyboard import _keyboard, row, bestiary_link_row
        kb = _keyboard([row(("🛒 Магазин", "shop")), bestiary_link_row()])
        send_message(
            f"❌ Для «{sub_action.label}» нужны товары: {names}. Купи их в магазине!",
            keyboard=kb,
        )
        return

    start_sub_action(db, care, sub_id, user.vk_id)
    steps = get_sub_steps(db, sub_id)
    if not steps:
        send_message(f"🐲 «{sub_action.label}» — нет шагов. Пропускаем.")
        from services.epic_service import advance_care
        advance_care(db, care)
        show_care_action(user, db, send_message, upload_image)
        return

    first_step = steps[0]
    dragon = get_epic_dragon(db, user.vk_id)
    name = get_epic_name(db, user.vk_id) or (dragon.name if dragon else "малыш")
    stage = get_stage(db, care.stage_id)

    user.state = epic_care_sub_state(care.stage_id)
    db.commit()

    msg = f"🐲 «{name}» — «{sub_action.label}»\n📝 {first_step.task or first_step.step_label}"
    if first_step.hint:
        msg += f"\n💡 {first_step.hint}"
    msg += f"\n\n🎯 Норма крестиков: {first_step.crosses_norm or 1000}\nВыбери режим:"
    action_img = getattr(first_step, "image_path", "") or ""
    attachment = _attach(upload_image, action_img, user.vk_id)
    send_message(msg, attachment=attachment, keyboard=sub_step_keyboard())


def handle_sub_mode(user, mode, db, send_message):
    from services.epic_service import get_care, get_current_sub_step
    care = get_care(db, user.vk_id)
    if not care or not care.current_sub_action_id:
        send_message("Уход не активен.")
        return

    sub_step = get_current_sub_step(db, care)
    if not sub_step:
        send_message("Шаг не найден.")
        return

    norm = sub_step.crosses_norm or 1000
    required = norm * 2 if mode == "x2" else norm

    user.state = epic_care_sub_state(care.stage_id, mode)
    if mode == "x2":
        care.sub_had_penalty = True
    db.commit()

    label = "⚠ Режим «Штраф (x2)»" if mode == "x2" else "✅ Режим «Норма»"
    send_message(
        f"{label} — нужно вышить не менее {required} крестиков.\n"
        f"Отправь одним сообщением фото работы и текст: «вышито {required}»."
    )


def handle_sub_message(user, text, attachments, db, send_message, upload_image=None):
    from services.epic_service import (
        get_care, get_current_sub_step, get_sub_steps,
        advance_sub_step, resolve_outcome, get_sub_action,
        advance_care, get_epic_dragon, get_epic_name,
    )
    care = get_care(db, user.vk_id)
    if not care or not care.current_sub_action_id:
        user.state = IDLE
        db.commit()
        send_message("Уход не активен.")
        return True

    sub_step = get_current_sub_step(db, care)
    if not sub_step:
        user.state = IDLE
        db.commit()
        send_message("Шаг не найден.")
        return True

    mode = state_mode(user.state)
    base_norm = sub_step.crosses_norm or 1000
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
            f"❌ Вы вышили {crosses} крестиков, а нужно не менее {required}.\n"
            f"Вышивайте дальше и отправьте повторно фото и «вышито [число]»."
        )
        return True

    photos = [a["photo"] for a in attachments if a.get("type") == "photo" and a.get("photo")]
    if not photos:
        send_message("❌ Прикрепи фото работы вместе с текстом «вышито [число]».")
        return True

    def fmt_photo(p):
        return f"photo{p['owner_id']}_{p['id']}"

    photo_before_id = fmt_photo(photos[0])
    photo_after_id = fmt_photo(photos[1]) if len(photos) > 1 else ""

    from services.epic_service import get_epic_dragon
    epic_dragon = get_epic_dragon(db, user.vk_id)

    credit_stitches(db, user.vk_id, crosses)
    if is_suspicious(crosses, required):
        create_suspicious_report(
            db, user.vk_id, epic_dragon.id if epic_dragon else None,
            0, crosses, required, mode,
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
            raw_message=text,
        )
        send_message(
            "⚠ Твой отчёт кажется подозрительным и отправлен на проверку. "
            "Крестики зачислены, но администратор может скорректировать баланс."
        )
        notify_admin(
            f"⚠ Подозрительный отчёт (составной уход) от id{user.vk_id}\n"
            f"Режим {mode}\nЗаявлено: {crosses}, норма: {required}\n"
            f"https://vk.com/gim239999455/convo/{user.vk_id}"
        )

    name = get_epic_name(db, user.vk_id) or (epic_dragon.name if epic_dragon else "малыш")
    result = advance_sub_step(db, care)

    if result == "outcome":
        sub_action = get_sub_action(db, care.current_sub_action_id) if care.current_sub_action_id else None
        if sub_action:
            outcome, polarity = resolve_outcome(db, user.vk_id, care, sub_action)
        else:
            outcome, polarity = None, "positive"

        if outcome:
            pol_label = "🌟" if polarity == "positive" else "💔"
            msg = f"{pol_label} «{sub_action.label if sub_action else '?'}» — {outcome.moodlet_title or outcome.label}"
            if outcome.moodlet_text:
                msg += f"\n\n{outcome.moodlet_text}"
            if outcome.image_path:
                attachment = _attach(upload_image, outcome.image_path, user.vk_id)
                send_message(msg, attachment=attachment)
            else:
                send_message(msg)

        send_message(f"✅ Забота о «{name}» завершена!")

        event = advance_care(db, care)
        kind = event.get("event")

        if kind == "finale":
            _finale(user, db, send_message, upload_image, event)
            return True

        if kind == "stage_up":
            nxt = event["stage"]
            send_message(f"🌟 «{name}» перешёл на новую стадию: «{nxt.name}»!")

        show_care_action(user, db, send_message, upload_image)
        return True

    send_message(f"✅ Шаг «{sub_step.step_label}» завершён!")
    next_step = get_current_sub_step(db, care)
    if next_step:
        dragon = get_epic_dragon(db, user.vk_id)
        name2 = get_epic_name(db, user.vk_id) or (dragon.name if dragon else "малыш")
        msg = f"🐲 «{name2}»\n📝 {next_step.task or next_step.step_label}"
        if next_step.hint:
            msg += f"\n💡 {next_step.hint}"
        msg += f"\n\n🎯 Норма крестиков: {next_step.crosses_norm or 1000}\nВыбери режим:"
        from bot.keyboard import sub_step_keyboard
        action_img = getattr(next_step, "image_path", "") or ""
        attachment = _attach(upload_image, action_img, user.vk_id)
        user.state = epic_care_sub_state(care.stage_id)
        db.commit()
        send_message(msg, attachment=attachment, keyboard=sub_step_keyboard())
    return True


def _award_action_moodlet(db, vk_id, care, action):
    from models import EpicMoodlet
    from services.epic_service import get_epic_user_dragon
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return
    key = f"action:{action.id}"
    exists = db.query(EpicMoodlet).filter(
        EpicMoodlet.user_dragon_id == ud.id, EpicMoodlet.key == key
    ).first()
    if exists:
        return
    from datetime import datetime
    db.add(EpicMoodlet(
        user_dragon_id=ud.id, key=key,
        title=f"Впервые: {action.action_label}",
        stage_id=care.stage_id,
        acquired_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    ))
    db.commit()


def _finale(user, db, send_message, upload_image, event):
    """Finale — dragon flies away, offer restart. (Phase 6)"""
    from services.epic_service import get_epic_name, get_epic_dragon
    import json
    name = get_epic_name(db, user.vk_id) or "малыш"
    dragon = get_epic_dragon(db, user.vk_id)

    _finalize_epic(db, user.vk_id)

    user.state = AWAIT_EPIC_RESTART
    db.commit()

    attachment = ""
    if upload_image and dragon and dragon.dragon_path:
        fp = os.path.join(_IMAGES, os.path.basename(dragon.dragon_path))
        if os.path.isfile(fp):
            attachment = upload_image(fp, peer_id=user.vk_id)

    summary = _character_summary(db, user.vk_id)
    msg = (
        f"🐲✨ «{name}» вырос и стал взрослым драконом!\n"
        f"Он расправил крылья и улетел в небо, оставив тёплые воспоминания.\n"
    )
    if summary:
        msg += f"\n🎭 Характер: {summary}\n"
    msg += "\nОн подкинул под дверь новое яйцо. Кого будем растить дальше?"

    kb = json.dumps({
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "🐲 Такого же заново", "payload": json.dumps({"cmd": "epic_restart", "mode": "same"}, ensure_ascii=False)}, "color": "primary"}],
            [{"action": {"type": "text", "label": "🎲 Нового случайного", "payload": json.dumps({"cmd": "epic_restart", "mode": "random"}, ensure_ascii=False)}, "color": "secondary"}],
            [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.com/app54663330"}}],
        ],
    }, ensure_ascii=False)
    send_message(msg, attachment=attachment, keyboard=kb)


def _finalize_epic(db, vk_id):
    """Mark the epic dragon as collected (flown away)."""
    from datetime import datetime
    from services.epic_service import get_epic_user_dragon
    ud = get_epic_user_dragon(db, vk_id)
    if ud and not ud.completed_at:
        ud.completed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        db.commit()


def _character_summary(db, vk_id):
    from services.epic_service import get_epic_user_dragon
    from services.character_service import character_summary
    ud = get_epic_user_dragon(db, vk_id)
    if not ud:
        return ""
    items = character_summary(db, ud.id)
    return ", ".join(item["label"] for item in items)


def handle_epic_restart(user, mode, db, send_message, upload_image=None):
    from services.epic_service import restart_epic
    from bot.handlers.epic import handle_epic_command
    dragon, had_others = restart_epic(db, vk_id=user.vk_id, mode=mode)
    user.state = IDLE
    db.commit()
    if not dragon:
        send_message("Пул эпических пуст. Загляни позже.")
        return
    if mode == "random" and not had_others:
        send_message("Других видов эпических пока нет — вернулся тот же вид.")
    send_message("🥚 Новое эпическое яйцо появилось! Начнём с выращивания.")
    handle_epic_command(user, db, send_message, upload_image)
