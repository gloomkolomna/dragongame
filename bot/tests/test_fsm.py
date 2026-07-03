from bot.fsm import IDLE, AWAIT_PIN, AWAIT_GARDEN, GROW_STEP, COMPLETED, grow_state, step_from_state, is_growing


def test_grow_state():
    assert grow_state(1) == "grow_step_1"
    assert grow_state(5) == "grow_step_5"


def test_step_from_state():
    assert step_from_state("grow_step_1") == 1
    assert step_from_state("grow_step_10") == 10
    assert step_from_state("idle") == 0
    assert step_from_state("") == 0


def test_is_growing():
    assert is_growing("grow_step_1") is True
    assert is_growing("grow_step_5") is True
    assert is_growing(AWAIT_PIN) is True
    assert is_growing(COMPLETED) is True
    assert is_growing(IDLE) is False
    assert is_growing(AWAIT_GARDEN) is False


def test_constants():
    assert IDLE == "idle"
    assert AWAIT_PIN == "await_pin"
    assert AWAIT_GARDEN == "await_garden"
    assert GROW_STEP == "grow_step"
    assert COMPLETED == "completed"
