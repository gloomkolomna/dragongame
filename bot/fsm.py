"""FSM — Finite State Machine for bot user states."""

IDLE = "idle"
AWAIT_PIN = "await_pin"
AWAIT_GARDEN = "await_garden"
GROW_STEP = "grow_step"
COMPLETED = "completed"


def grow_state(step: int) -> str:
    return f"grow_step_{step}"


def step_from_state(state: str) -> int:
    if state.startswith("grow_step_"):
        try:
            return int(state.split("_")[-1])
        except ValueError:
            pass
    return 0


def is_growing(state: str) -> bool:
    return state.startswith("grow_step_") or state == AWAIT_PIN or state == COMPLETED
