import json
from datetime import datetime, timedelta
from models import Dragon, DragonReservation, User, UserDragon
from bot.fsm import AWAIT_PIN, AWAIT_PIN_LIST, AWAIT_GARDEN, IDLE, grow_state
from bot.handlers.pin import handle_my_pins, handle_pin_entry, handle_activate_by_number, cancel_pin_list, handle_activate_all
from bot.services.pin_service import activate_pin_silently


def _make_dragon(db, name, pin):
    d = Dragon(name=name, rarity=1, steps_count=2, is_active=True, pin_code=pin)
    db.add(d)
    db.flush()
    return d


def _make_reservation(db, dragon_id, vk_id):
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    r = DragonReservation(
        vk_url=f"https://vk.ru/id{vk_id}",
        vk_user_id=vk_id,
        dragon_id=dragon_id,
        is_activated=False,
        created_at=now,
        updated_at=now,
    )
    db.add(r)
    return r


def _capture():
    sent = []

    def send(message, keyboard=None, attachment=""):
        sent.append(message)

    return send, sent


def test_handle_my_pins_keeps_state_and_populates_pin_list(db):
    dragon = _make_dragon(db, "ListDrag", "9585K")
    db.commit()
    _make_reservation(db, dragon.id, 555)
    db.commit()

    user = User(vk_id=555, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, sent = _capture()
    handle_my_pins(user, db, send)

    assert any("9585K" in m for m in sent)
    sd = json.loads(user.state_data or "{}")
    assert sd.get("_pin_list") == [dragon.id]
    assert user.state == AWAIT_PIN_LIST
    assert sd.get("_pin_list_prev_state") == AWAIT_PIN


def test_my_pins_single_hides_send_number_hint(db):
    dragon = _make_dragon(db, "Single", "SING1")
    db.commit()
    _make_reservation(db, dragon.id, 556)
    db.commit()

    user = User(vk_id=556, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, sent = _capture()
    handle_my_pins(user, db, send)

    body = "\n".join(sent)
    assert "Отправь номер из списка" not in body
    assert "Или несколько через запятую" not in body
    assert "Активировать все" in body


def test_my_pins_multiple_shows_send_number_hint(db):
    d1 = _make_dragon(db, "Many1", "MANY1")
    d2 = _make_dragon(db, "Many2", "MANY2")
    d3 = _make_dragon(db, "Many3", "MANY3")
    db.commit()
    for d in (d1, d2, d3):
        _make_reservation(db, d.id, 557)
    db.commit()

    user = User(vk_id=557, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, sent = _capture()
    handle_my_pins(user, db, send)

    body = "\n".join(sent)
    assert "Отправь номер из списка" in body
    assert "Или несколько через запятую" in body
    assert "Активировать все" in body


def test_activate_by_number_works_from_await_pin(db):
    dragon = _make_dragon(db, "NumDrag", "1234A")
    db.commit()
    _make_reservation(db, dragon.id, 600)
    db.commit()

    user = User(vk_id=600, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, _ = _capture()
    handle_my_pins(user, db, send)

    send2, sent2 = _capture()
    result = handle_activate_by_number(user, "1", db, send2)
    assert result is True
    assert any("Активировано" in m for m in sent2)

    ud = db.query(UserDragon).filter(
        UserDragon.user_id == 600, UserDragon.dragon_id == dragon.id
    ).first()
    assert ud is not None


def test_pin_entry_rejects_single_digit_after_my_pins(db):
    dragon = _make_dragon(db, "PinDrag", "9585K")
    db.commit()
    _make_reservation(db, dragon.id, 777)
    db.commit()

    user = User(vk_id=777, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, _ = _capture()
    handle_my_pins(user, db, send)

    send2, sent2 = _capture()
    handle_pin_entry(user, "1", db, send2)
    assert any("5 символов" in m for m in sent2)

    ud = db.query(UserDragon).filter(
        UserDragon.user_id == 777, UserDragon.dragon_id == dragon.id
    ).first()
    assert ud is None


def test_real_pin_still_works_via_pin_entry_after_my_pins(db):
    dragon = _make_dragon(db, "RealPin", "9585K")
    db.commit()
    _make_reservation(db, dragon.id, 888)
    db.commit()

    user = User(vk_id=888, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, _ = _capture()
    handle_my_pins(user, db, send)

    send2, _ = _capture()
    handle_pin_entry(user, "9585K", db, send2, upload_image=None)

    ud = db.query(UserDragon).filter(
        UserDragon.user_id == 888, UserDragon.dragon_id == dragon.id
    ).first()
    assert ud is not None
    assert user.state == grow_state(1)
    assert user.current_dragon_id == dragon.id


def test_send_seven_activates_seventh_of_ten(db):
    dragons = []
    base = datetime.now()
    for i in range(10):
        d = _make_dragon(db, f"Egg{i}", f"EG{i:03d}")
        dragons.append(d)
    db.commit()

    for idx, d in enumerate(dragons):
        now = (base + timedelta(seconds=idx)).strftime("%Y-%m-%dT%H:%M:%S")
        r = DragonReservation(
            vk_url="https://vk.ru/id950",
            vk_user_id=950,
            dragon_id=d.id,
            is_activated=False,
            created_at=now,
            updated_at=now,
        )
        db.add(r)
    db.commit()

    user = User(vk_id=950, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, sent = _capture()
    handle_my_pins(user, db, send)

    sd = json.loads(user.state_data or "{}")
    pin_list = sd.get("_pin_list", [])
    assert len(pin_list) == 10
    expected_7th = pin_list[6]

    body = "\n".join(sent)
    pos1 = body.find("1.")
    pos7 = body.find("7.")
    pos8 = body.find("8.")
    assert 0 <= pos1 < pos7 < pos8

    send2, sent2 = _capture()
    result = handle_activate_by_number(user, "7", db, send2)
    assert result is True
    assert any("Активировано" in m for m in sent2)

    activated = db.query(UserDragon).filter(
        UserDragon.user_id == 950, UserDragon.dragon_id == expected_7th
    ).first()
    assert activated is not None

    others = db.query(UserDragon).filter(
        UserDragon.user_id == 950
    ).count()
    assert others == 1


def test_send_zero_does_not_activate(db):
    d1 = _make_dragon(db, "Zero1", "ZER01")
    d2 = _make_dragon(db, "Zero2", "ZER02")
    db.commit()
    _make_reservation(db, d1.id, 960)
    _make_reservation(db, d2.id, 960)
    db.commit()

    user = User(vk_id=960, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, _ = _capture()
    handle_my_pins(user, db, send)

    send2, _ = _capture()
    result = handle_activate_by_number(user, "0", db, send2)
    assert result is False

    cnt = db.query(UserDragon).filter(UserDragon.user_id == 960).count()
    assert cnt == 0


def test_send_eleven_out_of_ten_does_not_activate(db):
    for i in range(10):
        d = _make_dragon(db, f"Out{i}", f"OT{i:03d}")
        _make_reservation(db, d.id, 970)
    db.commit()

    user = User(vk_id=970, state=AWAIT_PIN)
    db.add(user)
    db.commit()

    send, _ = _capture()
    handle_my_pins(user, db, send)

    send2, _ = _capture()
    result = handle_activate_by_number(user, "11", db, send2)
    assert result is False

    cnt = db.query(UserDragon).filter(UserDragon.user_id == 970).count()
    assert cnt == 0


def test_digit_in_await_garden_does_not_activate_pin(db):
    dragon = _make_dragon(db, "GardenPin", "GPIN1")
    db.commit()
    _make_reservation(db, dragon.id, 980)
    db.commit()

    user = User(vk_id=980, state=AWAIT_GARDEN)
    db.add(user)
    db.commit()

    result = handle_activate_by_number(user, "1", db, lambda *a, **k: None)
    assert result is False

    cnt = db.query(UserDragon).filter(UserDragon.user_id == 980).count()
    assert cnt == 0
    assert user.state == AWAIT_GARDEN


def test_cancel_pin_list_restores_prev_state(db):
    dragon = _make_dragon(db, "CancelDrag", "CAN01")
    db.commit()
    _make_reservation(db, dragon.id, 981)
    db.commit()

    user = User(vk_id=981, state=AWAIT_GARDEN)
    db.add(user)
    db.commit()

    send, _ = _capture()
    handle_my_pins(user, db, send)
    assert user.state == AWAIT_PIN_LIST

    cancel_pin_list(user, db, lambda *a, **k: None)
    assert user.state == AWAIT_GARDEN

    sd = json.loads(user.state_data or "{}")
    assert "_pin_list" not in sd
    assert "_pin_list_prev_state" not in sd


def test_activate_by_number_restores_prev_state(db):
    dragon = _make_dragon(db, "RestoreDrag", "RST01")
    db.commit()
    _make_reservation(db, dragon.id, 982)
    db.commit()

    user = User(vk_id=982, state=AWAIT_GARDEN)
    db.add(user)
    db.commit()

    send, _ = _capture()
    handle_my_pins(user, db, send)
    assert user.state == AWAIT_PIN_LIST

    send2, _ = _capture()
    handle_activate_by_number(user, "1", db, send2)
    assert user.state == AWAIT_GARDEN

    sd = json.loads(user.state_data or "{}")
    assert "_pin_list" not in sd
    assert "_pin_list_prev_state" not in sd


def test_activate_all_restores_prev_state(db):
    d1 = _make_dragon(db, "AllDrag1", "ALL01")
    d2 = _make_dragon(db, "AllDrag2", "ALL02")
    db.commit()
    _make_reservation(db, d1.id, 983)
    _make_reservation(db, d2.id, 983)
    db.commit()

    user = User(vk_id=983, state=AWAIT_GARDEN)
    db.add(user)
    db.commit()

    send, _ = _capture()
    handle_my_pins(user, db, send)
    assert user.state == AWAIT_PIN_LIST

    handle_activate_all(user, db, lambda *a, **k: None)
    assert user.state == AWAIT_GARDEN

    sd = json.loads(user.state_data or "{}")
    assert "_pin_list" not in sd
    assert "_pin_list_prev_state" not in sd


def test_manual_pin_command_clears_pin_list_prev_state(db):
    dragon = _make_dragon(db, "ManualDrag", "MAN01")
    db.commit()
    _make_reservation(db, dragon.id, 984)
    db.commit()

    user = User(vk_id=984, state=AWAIT_PIN_LIST)
    db.add(user)
    sd = {"_pin_list_prev_state": AWAIT_GARDEN}
    user.state_data = json.dumps(sd)
    db.commit()

    from bot.handlers.pin import handle_pin_command
    handle_pin_command(user, db, lambda *a, **k: None)
    assert user.state == AWAIT_PIN

    sd = json.loads(user.state_data or "{}")
    assert "_pin_list_prev_state" not in sd
    assert "_pin_list" not in sd
