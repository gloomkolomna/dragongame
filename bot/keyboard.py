"""VK Keyboard builder — returns JSON for vk.messages.send(keyboard=...)."""

import json

MINIAPP_URL = "https://vk.com/app54663330"


def _keyboard(buttons, one_time=False):
    return json.dumps({
        "one_time": one_time,
        "buttons": buttons,
    }, ensure_ascii=False)


def row(*labels_and_payloads):
    btns = []
    for item in labels_and_payloads:
        if isinstance(item, tuple):
            label, cmd = item
        else:
            label = item
            cmd = label
        is_primary = ("перейти" in label.lower() or "норма" in label.lower()) and "сменить" not in label.lower() and "штраф" not in label.lower()
        btns.append({
            "action": {
                "type": "text",
                "label": label,
                "payload": json.dumps({"cmd": cmd}, ensure_ascii=False),
            },
            "color": "primary" if is_primary else "secondary",
        })
    return btns


def bestiary_link_row():
    return [{
        "action": {
            "type": "open_link",
            "label": "📖 Мой Бестиарий",
            "link": MINIAPP_URL,
        },
    }]


def garden_row():
    return row(("📖 Список Бестиария", "garden"))


def help_rules_row():
    return row(("📜 Правила", "rules"), ("❓ Помощь", "help"))


def legends_row():
    return row(("🐲 Легендарные драконы", "legends"))


def epics_row():
    return row(("🐉 Эпические драконы", "epics"))


def incubator_row():
    return row(("🥚 Инкубатор", "incubator"))


def keyboard_with_legends(kb_json):
    data = json.loads(kb_json)
    buttons = data.get("buttons", [])
    for r in buttons:
        for b in r:
            payload = b.get("action", {}).get("payload")
            if payload:
                try:
                    if json.loads(payload).get("cmd") == "legends":
                        return kb_json
                except (json.JSONDecodeError, TypeError):
                    pass
    if len(buttons) >= 10:
        return kb_json
    insert_at = len(buttons)
    for i, r in enumerate(buttons):
        if any(b.get("action", {}).get("type") == "open_link" for b in r):
            insert_at = i
            break
    buttons.insert(insert_at, legends_row())
    data["buttons"] = buttons
    return json.dumps(data, ensure_ascii=False)


def keyboard_with_epics(kb_json):
    data = json.loads(kb_json)
    buttons = data.get("buttons", [])
    for r in buttons:
        for b in r:
            payload = b.get("action", {}).get("payload")
            if payload:
                try:
                    if json.loads(payload).get("cmd") == "epics":
                        return kb_json
                except (json.JSONDecodeError, TypeError):
                    pass
    if len(buttons) >= 10:
        return kb_json
    insert_at = len(buttons)
    for i, r in enumerate(buttons):
        if any(b.get("action", {}).get("type") == "open_link" for b in r):
            insert_at = i
            break
    buttons.insert(insert_at, epics_row())
    data["buttons"] = buttons
    return json.dumps(data, ensure_ascii=False)


def keyboard_with_incubator(kb_json):
    data = json.loads(kb_json)
    buttons = data.get("buttons", [])
    for r in buttons:
        for b in r:
            payload = b.get("action", {}).get("payload")
            if payload:
                try:
                    if json.loads(payload).get("cmd") == "incubator":
                        return kb_json
                except (json.JSONDecodeError, TypeError):
                    pass
    if len(buttons) >= 10:
        return kb_json
    insert_at = len(buttons)
    for i, r in enumerate(buttons):
        if any(b.get("action", {}).get("type") == "open_link" for b in r):
            insert_at = i
            break
    buttons.insert(insert_at, incubator_row())
    data["buttons"] = buttons
    return json.dumps(data, ensure_ascii=False)


def idle_keyboard(has_active=True):
    bottom = [("📖 Список Бестиария", "garden"), ("📜 Правила", "rules"), ("❓ Помощь", "help")]
    return _keyboard([
        row(("🛒 Магазин", "shop")),
        row(*bottom),
        bestiary_link_row(),
    ])


def growing_keyboard():
    return _keyboard([
        row(("🛒 Магазин", "shop")),
        row(("📖 Список Бестиария", "garden"), ("📜 Правила", "rules"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def waiting_keyboard():
    return _keyboard([
        row(("◀ Назад", "back")),
        row(("📖 Список Бестиария", "garden"), ("📜 Правила", "rules"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def start_growing_keyboard():
    return _keyboard([
        row(("🌱 Перейти к выращиванию", "grow")),
        row(("📖 Список Бестиария", "garden"), ("📜 Правила", "rules"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def step_buttons_keyboard():
    return _keyboard([
        [{"action": {"type": "text", "label": "🎯 Норма", "payload": json.dumps({"cmd": "norm"}, ensure_ascii=False)}, "color": "positive"}],
        [{"action": {"type": "text", "label": "⚡ Штраф (x2)", "payload": json.dumps({"cmd": "x2"}, ensure_ascii=False)}, "color": "negative"}],
        garden_row(),
        help_rules_row(),
        bestiary_link_row(),
    ])


def legend_buttons_keyboard():
    return _keyboard([
        [{"action": {"type": "text", "label": "🎯 Норма", "payload": json.dumps({"cmd": "norm"}, ensure_ascii=False)}, "color": "positive"}],
        [{"action": {"type": "text", "label": "⚡ Штраф (x2)", "payload": json.dumps({"cmd": "x2"}, ensure_ascii=False)}, "color": "negative"}],
        garden_row(),
        help_rules_row(),
        bestiary_link_row(),
    ])


def legend_next_keyboard():
    return _keyboard([
        [{"action": {"type": "text", "label": "📖 Читать следующий отрывок", "payload": json.dumps({"cmd": "legend_next"}, ensure_ascii=False)}, "color": "primary"}],
        garden_row(),
        bestiary_link_row(),
    ])


def epic_egg_buttons_keyboard():
    return _keyboard([
        [{"action": {"type": "text", "label": "🎯 Норма", "payload": json.dumps({"cmd": "norm"}, ensure_ascii=False)}, "color": "positive"}],
        [{"action": {"type": "text", "label": "⚡ Штраф (x2)", "payload": json.dumps({"cmd": "x2"}, ensure_ascii=False)}, "color": "negative"}],
        garden_row(),
        help_rules_row(),
        bestiary_link_row(),
    ])


def epic_care_keyboard():
    return _keyboard([
        [{"action": {"type": "text", "label": "🎯 Норма", "payload": json.dumps({"cmd": "norm"}, ensure_ascii=False)}, "color": "positive"}],
        [{"action": {"type": "text", "label": "⚡ Штраф (x2)", "payload": json.dumps({"cmd": "x2"}, ensure_ascii=False)}, "color": "negative"}],
        row(("🛒 Магазин", "shop")),
        garden_row(),
        help_rules_row(),
        bestiary_link_row(),
    ])


def epic_care_item_keyboard(button_label=""):
    label = (button_label or "🎒 Использовать")[:40]
    return _keyboard([
        [{"action": {"type": "text", "label": label, "payload": json.dumps({"cmd": "use_item"}, ensure_ascii=False)}, "color": "positive"}],
        row(("🛒 Магазин", "shop")),
        garden_row(),
        bestiary_link_row(),
    ])


def epic_care_optional_item_keyboard(button_label=""):
    label = (button_label or "🎒 Использовать")[:40]
    return _keyboard([
        [{"action": {"type": "text", "label": label, "payload": json.dumps({"cmd": "use_item"}, ensure_ascii=False)}, "color": "positive"}],
        [{"action": {"type": "text", "label": "⏭ Пропустить", "payload": json.dumps({"cmd": "skip_item"}, ensure_ascii=False)}, "color": "secondary"}],
        row(("🛒 Магазин", "shop")),
        garden_row(),
        bestiary_link_row(),
    ])


def await_pin_keyboard():
    return _keyboard([
        row(("📖 Список Бестиария", "garden"), ("📜 Правила", "rules"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def epic_name_keyboard():
    return _keyboard([
        row(("📖 Список Бестиария", "garden"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def epic_restart_keyboard():
    return _keyboard([
        [{"action": {"type": "text", "label": "🐲 Такого же заново", "payload": json.dumps({"cmd": "epic_restart", "mode": "same"}, ensure_ascii=False)}, "color": "primary"}],
        [{"action": {"type": "text", "label": "🎲 Нового случайного", "payload": json.dumps({"cmd": "epic_restart", "mode": "random"}, ensure_ascii=False)}, "color": "secondary"}],
        row(("📖 Список Бестиария", "garden"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def await_garden_keyboard(with_cancel=False, show_incubator=False):
    buttons = [
        row(("🥚 Добавить яйцо дракона", "pin")),
    ]
    if show_incubator:
        buttons.append(incubator_row())
    bottom = []
    if with_cancel:
        bottom.insert(0, ("◀ Не менять", "garden_cancel"))
    if bottom:
        buttons.append(row(*bottom))
    buttons.append(bestiary_link_row())
    return _keyboard(buttons)


def shop_keyboard(buyable_items, page, total_pages):
    buttons = []
    for it in buyable_items:
        label = f"🛒 {it.name} ({it.cost_stitches})"
        buttons.append([{
            "action": {
                "type": "text",
                "label": label[:40],
                "payload": json.dumps({"cmd": "buy", "item_id": it.id}, ensure_ascii=False),
            },
            "color": "positive",
        }])
    nav = []
    if page > 0:
        nav.append({
            "action": {"type": "text", "label": "◀ Назад",
                       "payload": json.dumps({"cmd": "shop", "page": page - 1}, ensure_ascii=False)},
            "color": "secondary",
        })
    if page < total_pages - 1:
        nav.append({
            "action": {"type": "text", "label": "Вперёд ▶",
                       "payload": json.dumps({"cmd": "shop", "page": page + 1}, ensure_ascii=False)},
            "color": "secondary",
        })
    if nav:
        buttons.append(nav)
    buttons.append(row(("🎒 Мой инвентарь", "inventory"), ("🐲 К эпическому дракону", "epic")))
    buttons.append(garden_row())
    buttons.append(bestiary_link_row())
    return _keyboard(buttons)


def inventory_keyboard():
    return _keyboard([
        row(("🛒 Магазин", "shop")),
        row(("🐲 К эпическому дракону", "epic")),
        garden_row(),
        help_rules_row(),
        bestiary_link_row(),
    ])


def care_shop_keyboard():
    return _keyboard([
        row(("🛒 Магазин", "shop")),
        row(("◀ К дракону", "epic")),
        garden_row(),
        help_rules_row(),
        bestiary_link_row(),
    ])


def sub_action_keyboard(sub_actions, missing_map):
    buttons = []
    for sa in sub_actions:
        missing = missing_map.get(sa.id, [])
        if missing:
            label = f"🔒 {sa.label}"
        else:
            label = f"✅ {sa.label}"
        buttons.append([{
            "action": {
                "type": "text",
                "label": label[:40],
                "payload": json.dumps({"cmd": "choose_sub", "sub_id": sa.id}, ensure_ascii=False),
            },
            "color": "positive" if not missing else "secondary",
        }])
    buttons.append(row(("🛒 Магазин", "shop")))
    buttons.append(garden_row())
    buttons.append(bestiary_link_row())
    return _keyboard(buttons)


def sub_step_keyboard(with_back=False):
    buttons = [
        [{"action": {"type": "text", "label": "🎯 Норма", "payload": json.dumps({"cmd": "norm"}, ensure_ascii=False)}, "color": "positive"}],
        [{"action": {"type": "text", "label": "⚡ Штраф (x2)", "payload": json.dumps({"cmd": "x2"}, ensure_ascii=False)}, "color": "negative"}],
    ]
    if with_back:
        buttons.append([{"action": {"type": "text", "label": "◀ Назад к выбору", "payload": json.dumps({"cmd": "sub_back"}, ensure_ascii=False)}, "color": "secondary"}])
    buttons.append(garden_row())
    buttons.append(help_rules_row())
    buttons.append(bestiary_link_row())
    return _keyboard(buttons)


def sub_confirm_keyboard(button_label=""):
    label = (button_label or "✅ Подтвердить")[:40]
    return _keyboard([
        [{"action": {"type": "text", "label": label, "payload": json.dumps({"cmd": "confirm_sub"}, ensure_ascii=False)}, "color": "positive"}],
        [{"action": {"type": "text", "label": "◀ Назад к выбору", "payload": json.dumps({"cmd": "sub_back"}, ensure_ascii=False)}, "color": "secondary"}],
        garden_row(),
        bestiary_link_row(),
    ])


def outcome_keyboard():
    return _keyboard([
        row(("▶ Продолжить", "grow")),
    ])


def intro_keyboard():
    return _keyboard([
        [{"action": {"type": "text", "label": "📖 Читать дальше", "payload": json.dumps({"cmd": "intro_next"}, ensure_ascii=False)}, "color": "primary"}],
    ])


def intro_last_keyboard():
    return _keyboard([
        [{"action": {"type": "text", "label": "📖 Завершить чтение истории", "payload": json.dumps({"cmd": "intro_next"}, ensure_ascii=False)}, "color": "primary"}],
    ])


def empty_keyboard():
    return json.dumps({"one_time": False, "buttons": []}, ensure_ascii=False)


def rules_menu_keyboard(sections):
    buttons = []
    for key, title in sections:
        buttons.append([{
            "action": {
                "type": "text",
                "label": title[:40],
                "payload": json.dumps({"cmd": "rules_section", "section": key}, ensure_ascii=False),
            },
            "color": "secondary",
        }])
    buttons.append(row(("◀ Закрыть правила", "rules_close")))
    buttons.append(bestiary_link_row())
    return _keyboard(buttons)


def rules_section_keyboard():
    return _keyboard([
        row(("◀ К правилам", "rules"), ("❓ Закрыть", "rules_close")),
        bestiary_link_row(),
    ])


def incubator_keyboard(epics):
    buttons = [
        row(("0. Отмена", "incubator_cancel")),
        bestiary_link_row(),
    ]
    return _keyboard(buttons)
