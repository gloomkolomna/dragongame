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


def idle_keyboard(has_active=True):
    bottom = [("🔄🥚 Сменить яйцо дракона", "garden"), ("❓ Помощь", "help")]
    return _keyboard([
        row(("🥚 Добавить яйцо дракона", "pin")),
        row(*bottom),
        bestiary_link_row(),
    ])


def growing_keyboard():
    return _keyboard([
        row(("📋 Статус", "status")),
        row(("🔄🥚 Сменить яйцо дракона", "garden"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def waiting_keyboard():
    return _keyboard([
        row(("📋 Статус", "status")),
        row(("🔄🥚 Сменить яйцо дракона", "garden"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def start_growing_keyboard():
    return _keyboard([
        row(("🌱 Перейти к выращиванию", "grow")),
        row(("🔄🥚 Сменить яйцо дракона", "garden"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def step_buttons_keyboard():
    return _keyboard([
        row(("✅ Норма", "norm")),
        row(("⚠ Штраф (x2)", "x2")),
        row(("📋 Статус", "status"), ("🔄🥚 Сменить яйцо дракона", "garden")),
        bestiary_link_row(),
    ])


def await_pin_keyboard():
    return _keyboard([
        row(("🔄🥚 Сменить яйцо дракона", "garden"), ("❓ Помощь", "help")),
        bestiary_link_row(),
    ])


def await_garden_keyboard(with_cancel=False):
    buttons = [
        row(("🥚 Добавить яйцо дракона", "pin")),
    ]
    bottom = [("🔄🥚 Сменить яйцо дракона", "garden"), ("📋 Статус", "status")]
    if with_cancel:
        bottom.insert(0, ("◀ Не менять", "garden_cancel"))
    buttons.append(row(*bottom))
    buttons.append(bestiary_link_row())
    return _keyboard(buttons)
