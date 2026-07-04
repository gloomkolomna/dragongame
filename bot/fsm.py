"""FSM — Finite State Machine for bot user states."""

IDLE = "idle"
AWAIT_PIN = "await_pin"
AWAIT_GARDEN = "await_garden"
GROW_STEP = "grow_step"
COMPLETED = "completed"


def grow_state(step: int, suffix: str = "") -> str:
    base = f"grow_step_{step}"
    return f"{base}_{suffix}" if suffix else base


def step_from_state(state: str) -> int:
    if state.startswith("grow_step_"):
        parts = state.split("_")
        try:
            return int(parts[2])
        except (ValueError, IndexError):
            pass
    return 0


def is_growing(state: str) -> bool:
    return state.startswith("grow_step_") or state == AWAIT_PIN or state == COMPLETED


def is_waiting_text(state: str) -> bool:
    return state.startswith("grow_step_") and any(
        state.endswith(suf) for suf in ("_norm", "_x2")
    )


def state_mode(state: str) -> str:
    if state.endswith("_x2"):
        return "x2"
    if state.endswith("_norm"):
        return "norm"
    return ""
