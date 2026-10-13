from enum import StrEnum
from typing import Any, NotRequired, Protocol, TypedDict


class Termination(StrEnum):
    """Why the debate loop stopped."""

    GM_STOP = "gm_stop"
    MAX_ROUNDS = "max_rounds"


class Suggestion(TypedDict):
    action: str
    reason: str


class DebateState(TypedDict):
    context: str
    proposal: str
    # Current round only, keyed by advisor persona key in speaking order.
    suggestions: dict[str, Suggestion]
    transcript: list[str]
    final_action: str
    round: int
    max_rounds: int
    stop: bool
    termination: NotRequired[Termination]


def new_debate_state(context: str, max_rounds: int) -> DebateState:
    """Fresh state for one turn's debate."""

    return {
        "context": context,
        "proposal": "",
        "suggestions": {},
        "transcript": [],
        "final_action": "",
        "round": 0,
        "max_rounds": max_rounds,
        "stop": False,
    }


class NodeFn(Protocol):
    """A graph node: reads state, returns a partial state update."""

    def __call__(self, state: DebateState) -> dict[str, Any]: ...


class RouterFn(Protocol):
    """Chooses the next node name from the current state."""

    def __call__(self, state: DebateState) -> str: ...
