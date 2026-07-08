import json

from bot import keyboard


def _all_keyboards():
    from types import SimpleNamespace
    shop_items = [SimpleNamespace(id=i, name=f"Item{i}", cost_stitches=100) for i in range(3)]
    return {
        "idle": keyboard.idle_keyboard(has_active=True),
        "idle_no_active": keyboard.idle_keyboard(has_active=False),
        "growing": keyboard.growing_keyboard(),
        "waiting": keyboard.waiting_keyboard(),
        "start_growing": keyboard.start_growing_keyboard(),
        "step_buttons": keyboard.step_buttons_keyboard(),
        "await_pin": keyboard.await_pin_keyboard(),
        "await_garden": keyboard.await_garden_keyboard(with_cancel=False),
        "await_garden_cancel": keyboard.await_garden_keyboard(with_cancel=True),
        "legend": keyboard.legend_buttons_keyboard(),
        "epic_egg": keyboard.epic_egg_buttons_keyboard(),
        "epic_care": keyboard.epic_care_keyboard(),
        "shop": keyboard.shop_keyboard(shop_items, page=0, total_pages=1),
    }


def _cmds(kb):
    cmds = set()
    for r in json.loads(kb)["buttons"]:
        for b in r:
            payload = b["action"].get("payload")
            if payload:
                cmds.add(json.loads(payload).get("cmd"))
    return cmds


def test_no_empty_rows():
    for name, kb in _all_keyboards().items():
        rows = json.loads(kb)["buttons"]
        for i, r in enumerate(rows):
            assert len(r) >= 1, f"{name} row {i} is empty"


def test_max_five_columns():
    for name, kb in _all_keyboards().items():
        rows = json.loads(kb)["buttons"]
        for i, r in enumerate(rows):
            assert len(r) <= 5, f"{name} row {i} has too many columns"


def test_shop_keyboard_cols():
    from types import SimpleNamespace
    items = [SimpleNamespace(id=i, name=f"Item{i}", cost_stitches=100) for i in range(5)]
    kb = keyboard.shop_keyboard(items, page=1, total_pages=3)
    rows = json.loads(kb)["buttons"]
    for i, r in enumerate(rows):
        assert 1 <= len(r) <= 5, f"shop row {i} bad width"


def test_garden_button_present_everywhere():
    for name, kb in _all_keyboards().items():
        assert "garden" in _cmds(kb), f"{name} is missing the garden (change egg) button"
