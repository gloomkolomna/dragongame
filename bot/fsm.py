"""FSM — Finite State Machine for bot user states."""

IDLE = "idle"
AWAIT_PIN = "await_pin"
AWAIT_GARDEN = "await_garden"
GROW_STEP = "grow_step"
COMPLETED = "completed"
AWAIT_EPIC_NAME = "await_epic_name"
AWAIT_EPIC_RESTART = "await_epic_restart"
AWAIT_EPIC_EGG_INTRO = "await_epic_egg_intro"
AWAIT_LEGENDS = "await_legends"
AWAIT_EPICS = "await_epics"
AWAIT_RULES = "await_rules"


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


def legend_state(fragment: int, suffix: str = "") -> str:
    base = f"legend_{fragment}"
    return f"{base}_{suffix}" if suffix else base


def is_legend(state: str) -> bool:
    return state.startswith("legend_")


def legend_fragment_from_state(state: str) -> int:
    if state.startswith("legend_"):
        parts = state.split("_")
        try:
            return int(parts[1])
        except (ValueError, IndexError):
            pass
    return 0


def is_legend_waiting(state: str) -> bool:
    return state.startswith("legend_") and any(
        state.endswith(suf) for suf in ("_norm", "_x2")
    )


def epic_egg_state(step: int, suffix: str = "") -> str:
    base = f"epic_egg_{step}"
    return f"{base}_{suffix}" if suffix else base


def is_epic_egg(state: str) -> bool:
    return state.startswith("epic_egg_")


def epic_egg_step_from_state(state: str) -> int:
    if state.startswith("epic_egg_"):
        parts = state.split("_")
        try:
            return int(parts[2])
        except (ValueError, IndexError):
            pass
    return 0


def is_epic_egg_waiting(state: str) -> bool:
    return state.startswith("epic_egg_") and any(
        state.endswith(suf) for suf in ("_norm", "_x2")
    )


def epic_care_state(stage_id: int, suffix: str = "") -> str:
    base = f"epic_care_{stage_id}"
    return f"{base}_{suffix}" if suffix else base


def is_epic_care(state: str) -> bool:
    return state.startswith("epic_care_")


def is_epic_care_waiting(state: str) -> bool:
    return state.startswith("epic_care_") and any(
        state.endswith(suf) for suf in ("_norm", "_x2")
    )


def epic_care_sub_state(stage_id: int, suffix: str = "") -> str:
    base = f"epic_care_{stage_id}_sub"
    return f"{base}_{suffix}" if suffix else base


def epic_care_sub_confirm_state(stage_id: int) -> str:
    return f"epic_care_{stage_id}_sub_confirm"


def is_epic_care_sub_confirm(state: str) -> bool:
    return state.startswith("epic_care_") and state.endswith("_sub_confirm")


def is_epic_care_sub(state: str) -> bool:
    return state.startswith("epic_care_") and "_sub" in state


def is_epic_care_sub_waiting(state: str) -> bool:
    return state.startswith("epic_care_") and "_sub" in state and any(
        state.endswith(suf) for suf in ("_norm", "_x2")
    )


def intro_chapter_state(chapter: int) -> str:
    return f"intro_chapter_{chapter}"


def is_intro_chapter(state: str) -> bool:
    return state.startswith("intro_chapter_")


def intro_chapter_from_state(state: str) -> int:
    if state.startswith("intro_chapter_"):
        parts = state.split("_")
        try:
            return int(parts[2])
        except (ValueError, IndexError):
            pass
    return 0
