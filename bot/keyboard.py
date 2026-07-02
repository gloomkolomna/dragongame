"""VK Keyboard builder — returns JSON for vk.messages.send(keyboard=...)."""

import json


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
        btns.append({
            "action": {
                "type": "text",
                "label": label,
                "payload": json.dumps({"cmd": cmd}, ensure_ascii=False),
            },
            "color": "primary" if "дракон" in label.lower() or "подтвердить" in label.lower() else "secondary",
        })
    return btns


def idle_keyboard():
    return _keyboard([
        row(("🐉 Добавить дракона", "pin")),
        row(("📖 Мой Бестиарий", "garden"), ("❓ Помощь", "help")),
    ])


def growing_keyboard():
    return _keyboard([
        row(("📋 Статус", "status")),
        row(("📖 Мой Бестиарий", "garden"), ("❓ Помощь", "help")),
    ])


def await_pin_keyboard():
    return _keyboard([
        row(("📖 Мой Бестиарий", "garden"), ("❓ Помощь", "help")),
    ])


def await_garden_keyboard():
    return _keyboard([
        row(("🐉 Добавить дракона", "pin")),
        row(("📖 Мой Бестиарий", "garden"), ("📋 Статус", "status")),
    ])
