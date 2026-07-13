import json
from models import User
from bot.handlers.rules import (
    RULES_SECTIONS,
    SECTIONS_MENU_VIEW,
    SECTIONS_BY_KEY,
    handle_rules,
    handle_rules_section,
    handle_rules_pick,
    cancel_rules,
)
from bot.fsm import AWAIT_RULES, IDLE


def _make_user(db, state=IDLE):
    u = User(vk_id=101, state=state)
    db.add(u)
    db.commit()
    return u


def _capture():
    sent = []

    def send(msg, keyboard=None, **kw):
        sent.append({"text": msg, "keyboard": keyboard})

    return send, sent


def test_rules_menu_shows_all_sections(db):
    u = _make_user(db, state="grow_step_2")
    send, sent = _capture()

    handle_rules(u, db, send)

    assert u.state == AWAIT_RULES
    assert len(sent) == 1
    text = sent[0]["text"]
    for i, (key, title) in enumerate(SECTIONS_MENU_VIEW):
        assert f"{i + 1}." in text
        assert title in text
    assert "0" in text


def test_rules_saves_prev_state(db):
    u = _make_user(db, state="grow_step_2_norm")
    send, sent = _capture()

    handle_rules(u, db, send)

    saved = json.loads(u.state_data or "{}")
    assert saved.get("_rules_prev_state") == "grow_step_2_norm"


def test_rules_each_section_has_content():
    for key, title, body in RULES_SECTIONS:
        assert key
        assert title
        assert body
        assert len(body) > 50
        assert key in SECTIONS_BY_KEY


def test_rules_section_by_key(db):
    u = _make_user(db, state=AWAIT_RULES)
    send, sent = _capture()

    handle_rules_section(u, db, send, "epic")

    assert len(sent) == 1
    assert "ЭПИЧЕСКИЕ" in sent[0]["text"]


def test_rules_section_unknown_key_falls_back_to_menu(db):
    u = _make_user(db, state=AWAIT_RULES)
    send, sent = _capture()

    handle_rules_section(u, db, send, "nope")

    assert u.state == AWAIT_RULES
    assert "ПРАВИЛА ИГРЫ" in sent[0]["text"]


def test_rules_pick_by_number(db):
    u = _make_user(db, state=AWAIT_RULES)
    send, sent = _capture()

    handle_rules_pick(u, db, send, 1)

    assert len(sent) == 1
    assert "ВЫРАСТИТЬ ДРАКОНА" in sent[0]["text"]


def test_rules_pick_invalid_number_returns_menu(db):
    u = _make_user(db, state=AWAIT_RULES)
    send, sent = _capture()

    handle_rules_pick(u, db, send, 999)

    assert u.state == AWAIT_RULES
    assert "ПРАВИЛА ИГРЫ" in sent[0]["text"]


def test_rules_cancel_restores_prev_state(db):
    u = _make_user(db, state="grow_step_2_norm")
    sd = {"_rules_prev_state": "grow_step_2_norm"}
    u.state_data = json.dumps(sd)
    u.state = AWAIT_RULES
    db.commit()
    send, sent = _capture()

    cancel_rules(u, db, send)

    assert u.state == "grow_step_2_norm"
    sd_after = json.loads(u.state_data or "{}")
    assert "_rules_prev_state" not in sd_after
    assert "закрыты" in sent[0]["text"]


def test_rules_cancel_without_prev_state_goes_idle(db):
    u = _make_user(db, state=AWAIT_RULES)
    send, sent = _capture()

    cancel_rules(u, db, send)

    assert u.state == IDLE


def test_rules_keyword_recognized():
    from bot.main import extract_cmd

    assert extract_cmd("правила", "") == "rules"
    assert extract_cmd("покажи правила", "") == "rules"
    assert extract_cmd("/rules", "") == "rules"
    assert extract_cmd("Правила игры", "") == "rules"


def test_rules_section_payload_dispatches():
    from bot.main import extract_cmd

    assert extract_cmd("", '{"cmd":"rules_section","section":"epic"}') == "rules_section"
