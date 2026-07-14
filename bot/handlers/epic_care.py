"""Epic care handler — daily care cycle actions (Phase 5) + finale (Phase 6)."""

import os
import re
from bot.fsm import IDLE, AWAIT_EPIC_RESTART, AWAIT_EPIC_EGG_INTRO, epic_care_state, epic_care_sub_state, epic_care_sub_confirm_state, state_mode, is_epic_care_sub, is_epic_care_sub_waiting, is_epic_care_sub_confirm
from bot.services.grow_service import (
    credit_stitches, is_suspicious, is_blocked, create_suspicious_report, notify_admin,
)
from bot.keyboard import epic_care_keyboard, epic_care_item_keyboard, epic_care_optional_item_keyboard, idle_keyboard, sub_step_keyboard

_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")


def _notify_stage_up(name, nxt_stage, send_message, upload_image, vk_id):
    msg = f"🌟 «{name}» перешёл на новую стадию: «{nxt_stage.name}»!"
    attachment = _attach(upload_image, nxt_stage.image_start, vk_id)
    send_message(msg, attachment=attachment)


def _care_fallback_keyboard(db, vk_id):
    """Keyboard for care dead-ends so the player is never stuck without buttons."""
    import json as j
    kb = j.dumps({
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "📖 Список Бестиария", "payload": j.dumps({"cmd": "garden"}, ensure_ascii=False)}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "❓ Помощь", "payload": j.dumps({"cmd": "help"}, ensure_ascii=False)}, "color": "secondary"}],
            [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.com/app54663330"}}],
        ],
    }, ensure_ascii=False)
    try:
        from bot.handlers.epic import user_has_epic
        from bot.keyboard import keyboard_with_epics
        if user_has_epic(db, vk_id):
            kb = keyboard_with_epics(kb)
    except Exception:
        pass
    try:
        from bot.handlers.commands import user_has_legendary
        from bot.keyboard import keyboard_with_legends
        if user_has_legendary(db, vk_id):
            kb = keyboard_with_legends(kb)
    except Exception:
        pass
    return kb


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
        send_message(
            f"🐲 «{name}»: на стадии «{stage.name if stage else '?'}» нет действий ухода.",
            keyboard=_care_fallback_keyboard(db, user.vk_id),
        )
        return

    if getattr(action, "action_type", "simple") == "composite":
        _show_composite_action(user, db, send_message, upload_image, care, action, dragon, name, stage)
        return

    from services.epic_service import has_non_optional_items, missing_optional_action_items

    has_items = has_action_items(db, action.id)
    missing_non_opt = missing_action_items(db, user.vk_id, action.id) if has_items else []
    only_optional = has_items and not has_non_optional_items(db, action.id)

    base_msg = (
        f"🐲 «{name}» — стадия «{stage.name if stage else '?'}»\n"
        f"\n▶ {action.action_label}\n"
    )
    if action.hint:
        base_msg += f"💡 {action.hint}\n"

    if has_items:
        if missing_non_opt:
            names = ", ".join(f"«{m.name}»" for m in missing_non_opt)
            from bot.keyboard import care_shop_keyboard
            kb = care_shop_keyboard()
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
        msg = base_msg
        if getattr(action, "description", ""):
            msg += f"\n{action.description}\n"
        msg += f"\n📦 Товары: {item_names}\n"
        confirm_label = getattr(action, "confirm_button_label", "") or ""
        if only_optional:
            msg += f"Нажми «{confirm_label or '🎒 Использовать'}», если есть товары, или «⏭ Пропустить»."
            kb = epic_care_optional_item_keyboard(confirm_label)
        else:
            msg += f"Нажми «{confirm_label or '🎒 Использовать'}», чтобы подтвердить."
            kb = epic_care_item_keyboard(confirm_label)
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
        from bot.keyboard import care_shop_keyboard
        kb = care_shop_keyboard()
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
    _show_action_outcome(db, user.vk_id, care, action, send_message, upload_image)

    event = advance_care(db, care)
    kind = event.get("event")

    if kind == "finale":
        _finale(user, db, send_message, upload_image, event)
        return

    if kind == "stage_up":
        nxt = event["stage"]
        _notify_stage_up(name, nxt, send_message, upload_image, user.vk_id)

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
    _show_action_outcome(db, user.vk_id, care, action, send_message, upload_image)

    event = advance_care(db, care)
    kind = event.get("event")

    if kind == "finale":
        _finale(user, db, send_message, upload_image, event)
        return

    if kind == "stage_up":
        nxt = event["stage"]
        _notify_stage_up(name, nxt, send_message, upload_image, user.vk_id)

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

    if is_blocked(crosses, required):
        create_suspicious_report(
            db, user.vk_id, epic_dragon.id if epic_dragon else None,
            action.order_in_cycle, crosses, required, mode,
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
    _show_action_outcome(db, user.vk_id, care, action, send_message, upload_image, had_penalty=(mode == "x2"))

    event = advance_care(db, care)
    kind = event.get("event")

    if kind == "finale":
        _finale(user, db, send_message, upload_image, event)
        return True

    if kind == "stage_up":
        nxt = event["stage"]
        _notify_stage_up(name, nxt, send_message, upload_image, user.vk_id)

    show_care_action(user, db, send_message, upload_image)
    return True


# ─── Composite action handlers ───

def _show_composite_action(user, db, send_message, upload_image, care, action, dragon, name, stage):
    from services.epic_service import get_sub_actions, get_current_sub_step, get_sub_steps, sub_has_items, get_sub_action
    from bot.keyboard import sub_action_keyboard, sub_step_keyboard, sub_confirm_keyboard

    if care.current_sub_action_id:
        if is_epic_care_sub_confirm(user.state) and sub_has_items(db, care.current_sub_action_id):
            sub_action = get_sub_action(db, care.current_sub_action_id)
            if sub_action:
                user.state = epic_care_sub_confirm_state(care.stage_id)
                db.commit()
                msg = f"🐲 «{name}» — «{sub_action.label}»\n"
                if sub_action.description:
                    msg += f"\n{sub_action.description}\n"
                action_img = getattr(sub_action, "image_path", "") or ""
                attachment = _attach(upload_image, action_img, user.vk_id)
                send_message(msg, attachment=attachment, keyboard=sub_confirm_keyboard(sub_action.confirm_button_label))
                return
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
            send_message(msg, attachment=attachment, keyboard=sub_step_keyboard(with_back=(care.current_step_order or 0) == 0))
            return

    sub_actions = get_sub_actions(db, action.id)
    if not sub_actions:
        send_message(
            f"🐲 «{name}»: у действия «{action.action_label}» нет вариантов.",
            keyboard=_care_fallback_keyboard(db, user.vk_id),
        )
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
        get_care, get_sub_action, start_sub_action, select_sub_action, sub_has_items,
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
        from bot.keyboard import care_shop_keyboard
        kb = care_shop_keyboard()
        send_message(
            f"❌ Для «{sub_action.label}» нужны товары: {names}. Купи их в магазине!",
            keyboard=kb,
        )
        return

    dragon = get_epic_dragon(db, user.vk_id)
    name = get_epic_name(db, user.vk_id) or (dragon.name if dragon else "малыш")

    if sub_has_items(db, sub_id):
        select_sub_action(db, care, sub_id)
        user.state = epic_care_sub_confirm_state(care.stage_id)
        db.commit()
        msg = f"🐲 «{name}» — «{sub_action.label}»\n"
        if sub_action.description:
            msg += f"\n{sub_action.description}\n"
        from bot.keyboard import sub_confirm_keyboard
        action_img = getattr(sub_action, "image_path", "") or ""
        attachment = _attach(upload_image, action_img, user.vk_id)
        send_message(msg, attachment=attachment, keyboard=sub_confirm_keyboard(sub_action.confirm_button_label))
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
    stage = get_stage(db, care.stage_id)

    user.state = epic_care_sub_state(care.stage_id)
    db.commit()

    msg = f"🐲 «{name}» — «{sub_action.label}»\n📝 {first_step.task or first_step.step_label}"
    if first_step.hint:
        msg += f"\n💡 {first_step.hint}"
    msg += f"\n\n🎯 Норма крестиков: {first_step.crosses_norm or 1000}\nВыбери режим:"
    action_img = getattr(first_step, "image_path", "") or ""
    attachment = _attach(upload_image, action_img, user.vk_id)
    send_message(msg, attachment=attachment, keyboard=sub_step_keyboard(with_back=True))


def handle_confirm_sub(user, db, send_message, upload_image=None):
    from services.epic_service import (
        get_care, get_sub_action, consume_sub_items, missing_sub_items,
        get_sub_steps, get_epic_dragon, get_epic_name, get_stage,
        advance_care, resolve_outcome,
    )
    care = get_care(db, user.vk_id)
    if not care or not care.current_sub_action_id:
        user.state = IDLE
        db.commit()
        send_message("Уход не активен.")
        return

    sub_id = care.current_sub_action_id
    sub_action = get_sub_action(db, sub_id)
    if not sub_action:
        send_message("Вариант не найден.")
        return

    missing = missing_sub_items(db, user.vk_id, sub_id)
    if missing:
        names = ", ".join(f"«{m.name}»" for m in missing)
        from bot.keyboard import care_shop_keyboard
        kb = care_shop_keyboard()
        send_message(f"❌ У тебя нет {names}. Купи их в магазине!", keyboard=kb)
        return

    consume_sub_items(db, user.vk_id, sub_id)

    dragon = get_epic_dragon(db, user.vk_id)
    name = get_epic_name(db, user.vk_id) or (dragon.name if dragon else "малыш")

    steps = get_sub_steps(db, sub_id)
    if steps:
        first_step = steps[0]
        user.state = epic_care_sub_state(care.stage_id)
        db.commit()
        send_message(f"✅ «{sub_action.label}» — можно приступать!")
        msg = f"🐲 «{name}»\n📝 {first_step.task or first_step.step_label}"
        if first_step.hint:
            msg += f"\n💡 {first_step.hint}"
        msg += f"\n\n🎯 Норма крестиков: {first_step.crosses_norm or 1000}\nВыбери режим:"
        action_img = getattr(first_step, "image_path", "") or ""
        attachment = _attach(upload_image, action_img, user.vk_id)
        send_message(msg, attachment=attachment, keyboard=sub_step_keyboard())
        return

    outcome, polarity = resolve_outcome(db, user.vk_id, care, sub_action)
    if outcome:
        pol_label = "🌟" if polarity == "positive" else "💔"
        moodlet_title = outcome.moodlet_title or outcome.label
        msg = f"{pol_label} «{sub_action.label}»"
        if moodlet_title:
            msg += f" — {moodlet_title}"
        if outcome.moodlet_text:
            msg += f"\n\n{outcome.moodlet_text}"
        if moodlet_title or outcome.moodlet_text:
            msg += f"\n\nДобавлено воспоминание: {moodlet_title or 'без названия'}"
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
        return

    if kind == "stage_up":
        nxt = event["stage"]
        _notify_stage_up(name, nxt, send_message, upload_image, user.vk_id)

    show_care_action(user, db, send_message, upload_image)


def handle_sub_back(user, db, send_message, upload_image=None):
    from services.epic_service import (
        get_care, get_current_action, get_epic_dragon, get_epic_name,
        get_stage, restore_sub_items,
    )
    care = get_care(db, user.vk_id)
    if not care or not care.current_sub_action_id:
        show_care_action(user, db, send_message, upload_image)
        return

    if (care.current_step_order or 0) != 0:
        send_message("Вернуться к выбору уже нельзя — задание начато.")
        return

    sub_id = care.current_sub_action_id
    if not is_epic_care_sub_confirm(user.state):
        restore_sub_items(db, user.vk_id, sub_id)

    care.current_sub_action_id = None
    care.current_step_order = 0
    care.sub_had_penalty = False
    db.commit()

    action = get_current_action(db, care)
    dragon = get_epic_dragon(db, user.vk_id)
    name = get_epic_name(db, user.vk_id) or (dragon.name if dragon else "малыш")
    stage = get_stage(db, care.stage_id)
    if not action:
        show_care_action(user, db, send_message, upload_image)
        return
    _show_composite_action(user, db, send_message, upload_image, care, action, dragon, name, stage)


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

    if is_blocked(crosses, required):
        create_suspicious_report(
            db, user.vk_id, epic_dragon.id if epic_dragon else None,
            0, crosses, required, mode,
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
            moodlet_title = outcome.moodlet_title or outcome.label
            msg = f"{pol_label} «{sub_action.label if sub_action else '?'}»"
            if moodlet_title:
                msg += f" — {moodlet_title}"
            if outcome.moodlet_text:
                msg += f"\n\n{outcome.moodlet_text}"
            if moodlet_title or outcome.moodlet_text:
                msg += f"\n\nДобавлено воспоминание: {moodlet_title or 'без названия'}"
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
            _notify_stage_up(name, nxt, send_message, upload_image, user.vk_id)

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


def _show_action_outcome(db, vk_id, care, action, send_message, upload_image, had_penalty=False):
    from services.epic_service import resolve_action_outcome
    outcome, polarity = resolve_action_outcome(db, care, action, had_penalty=had_penalty)
    if not outcome:
        return
    pol_label = "🌟" if polarity == "positive" else "💔"
    moodlet_title = outcome.moodlet_title or outcome.label or action.action_label
    msg = f"{pol_label} {moodlet_title}" if moodlet_title else f"{pol_label} {action.action_label}"
    if outcome.moodlet_text:
        msg += f"\n\n{outcome.moodlet_text}"
    if moodlet_title or outcome.moodlet_text:
        label_for_memory = outcome.moodlet_title or outcome.label or action.action_label
        msg += f"\n\nДобавлено воспоминание: {label_for_memory}"
    if outcome.image_path:
        attachment = _attach(upload_image, outcome.image_path, vk_id)
        send_message(msg, attachment=attachment)
    else:
        send_message(msg)


def _finale(user, db, send_message, upload_image, event):
    from services.epic_service import get_epic_name, get_epic_dragon
    import json
    name = get_epic_name(db, user.vk_id) or "малыш"
    dragon = get_epic_dragon(db, user.vk_id)

    _finalize_epic(db, user.vk_id)

    attachment = ""
    if upload_image:
        image_to_show = None
        stage = event.get("stage")
        if dragon and dragon.finale_image_path:
            image_to_show = dragon.finale_image_path
        elif dragon and dragon.dragon_path:
            image_to_show = dragon.dragon_path
        elif stage and stage.image_end:
            image_to_show = stage.image_end
        elif dragon and dragon.egg_path:
            image_to_show = dragon.egg_path
        if image_to_show:
            fp = os.path.join(_IMAGES, os.path.basename(image_to_show))
            if os.path.isfile(fp):
                attachment = upload_image(fp, peer_id=user.vk_id)

    summary = _character_summary(db, user.vk_id)
    finale_text = (dragon.finale_description or "") if dragon and dragon.finale_description else ""
    if finale_text:
        msg = f"🐲✨ «{name}» вырос и стал взрослым драконом!\n{finale_text}\n"
    else:
        msg = (
            f"🐲✨ «{name}» вырос и стал взрослым драконом!\n"
            f"Он расправил крылья и улетел в небо, оставив тёплые воспоминания.\n"
        )
    if summary:
        msg += f"\n🎭 Характер: {summary}\n"

    new_dragon = _pick_free_epic(db, user.vk_id, dragon.id if dragon else None)
    if new_dragon:
        from models import UserDragon
        ud = UserDragon(user_id=user.vk_id, dragon_id=new_dragon.id, completed_at="")
        db.add(ud)
        db.flush()
        user.epic_dragon_id = new_dragon.id
        user.state = IDLE
        db.commit()

        msg += (
            f"\n🥚 Он подкинул под дверь новое яйцо — «{new_dragon.egg_type or new_dragon.name}»!"
        )
        send_message(msg, attachment=attachment)

        user.state = AWAIT_EPIC_EGG_INTRO
        sd = json.loads(user.state_data or "{}")
        sd["_needs_egg_intro"] = True
        user.state_data = json.dumps(sd, ensure_ascii=False)
        db.commit()
        from bot.keyboard import epic_egg_intro_keyboard
        send_message(
            f"🥚 Перед тобой новое эпическое яйцо — «{new_dragon.egg_type or new_dragon.name}».\n"
            "🌟 Нажми «Бережно принять яйцо», чтобы начать выращивание!",
            keyboard=epic_egg_intro_keyboard(),
        )
        return

    user.state = AWAIT_EPIC_RESTART
    db.commit()

    msg += "\nТы вырастил всех доступных эпических драконов! Хочешь пройти кого-то заново?"
    from bot.keyboard import epic_restart_keyboard
    send_message(msg, attachment=attachment, keyboard=epic_restart_keyboard())


def _pick_free_epic(db, vk_id, exclude_dragon_id=None):
    from models import Dragon, UserDragon
    completed_ids = set(
        row[0] for row in db.query(UserDragon.dragon_id).filter(
            UserDragon.user_id == vk_id,
            UserDragon.completed_at != "",
            UserDragon.completed_at != None,
        ).all()
    )
    pool = db.query(Dragon).filter(
        Dragon.is_epic == True,
        Dragon.is_active == True,
        Dragon.id.notin_(completed_ids) if completed_ids else True,
    ).all()
    if not pool:
        return None
    import random
    return random.choice(pool)


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
