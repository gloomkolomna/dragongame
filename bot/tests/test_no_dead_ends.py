import json
from bot.keyboard import (
    epic_name_keyboard,
    epic_restart_keyboard,
    care_shop_keyboard,
    await_garden_keyboard,
)


def _buttons_flat(kb_json):
    data = json.loads(kb_json)
    out = []
    for r in data.get("buttons", []):
        for b in r:
            payload = b.get("action", {}).get("payload", "")
            try:
                cmd = json.loads(payload).get("cmd", "") if payload else ""
            except (json.JSONDecodeError, TypeError):
                cmd = ""
            out.append({
                "label": b.get("action", {}).get("label", ""),
                "cmd": cmd,
                "type": b.get("action", {}).get("type", ""),
            })
    return out


def _has_cmd(kb_json, cmd):
    return any(b["cmd"] == cmd for b in _buttons_flat(kb_json))


def test_epic_name_keyboard_has_escape():
    kb = epic_name_keyboard()
    assert _has_cmd(kb, "garden")
    assert _has_cmd(kb, "help")


def test_epic_restart_keyboard_has_escape_and_restart():
    kb = epic_restart_keyboard()
    assert _has_cmd(kb, "garden")
    assert _has_cmd(kb, "help")
    assert _has_cmd(kb, "epic_restart")


def test_care_shop_keyboard_has_back_to_dragon():
    kb = care_shop_keyboard()
    assert _has_cmd(kb, "shop")
    assert _has_cmd(kb, "epic")
    assert _has_cmd(kb, "garden")


def test_await_garden_keyboard_cancel_persists():
    kb_with = await_garden_keyboard(with_cancel=True)
    assert _has_cmd(kb_with, "garden_cancel")


def test_get_keyboard_gives_escape_in_dead_end_states():
    from bot.main import get_keyboard
    from bot.fsm import AWAIT_EPIC_NAME, AWAIT_EPIC_RESTART, AWAIT_GARDEN
    from models import User

    for state in (AWAIT_EPIC_NAME, AWAIT_EPIC_RESTART):
        kb = get_keyboard(state)
        assert _has_cmd(kb, "garden"), f"нет выхода (garden) в состоянии {state}"

    kb = get_keyboard(AWAIT_GARDEN)
    assert _has_cmd(kb, "garden_cancel"), "кнопка «Не менять» должна показываться в AWAIT_GARDEN"
