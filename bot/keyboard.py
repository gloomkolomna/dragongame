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
        is_primary = ("дракон" in label.lower() or "подтвердить" in label.lower()) and "сменить" not in label.lower()
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
    bottom = [("🔄 Сменить дракона", "garden"), ("❓ Помощь", "help")]
    if not has_active:
        bottom = [("❓ Помощь", "help")]
    return _keyboard([
        bestiary_link_row(),
        row(("🐉 Добавить дракона", "pin")),
        row(*bottom),
    ])


def growing_keyboard():
    return _keyboard([
        bestiary_link_row(),
        row(("📋 Статус", "status")),
        row(("🔄 Сменить дракона", "garden"), ("❓ Помощь", "help")),
    ])


def await_pin_keyboard():
    return _keyboard([
        bestiary_link_row(),
        row(("🔄 Сменить дракона", "garden"), ("❓ Помощь", "help")),
    ])


def await_garden_keyboard(with_cancel=False):
    buttons = [
        bestiary_link_row(),
        row(("🐉 Добавить дракона", "pin")),
    ]
    bottom = [("🔄 Сменить дракона", "garden"), ("📋 Статус", "status")]
    if with_cancel:
        bottom.insert(0, ("◀ Не менять", "garden_cancel"))
    buttons.append(row(*bottom))
    return _keyboard(buttons)
