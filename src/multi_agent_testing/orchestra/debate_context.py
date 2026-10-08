
from enum import StrEnum
from typing import Any, NotRequired, Protocol, TypedDict


class Termination(StrEnum):
    """Why the debate loop stopped."""

    GM_STOP = "gm_stop"
    MAX_ROUNDS = "max_rounds"

class DebateState(TypedDict):
    context: str
    proposal: str
    alternative: str
    transcript: list[str]
    final_action: str
    round: int
    max_rounds: int
    stop: bool
    termination: NotRequired[Termination]

class NodeFn(Protocol):
    """A graph node: reads state, returns a partial state update."""

    def __call__(self, state: DebateState) -> dict[str, Any]: ...


class RouterFn(Protocol):
    """Chooses the next node name from the current state."""

    def __call__(self, state: DebateState) -> str: ...
