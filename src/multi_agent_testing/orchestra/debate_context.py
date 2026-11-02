from enum import StrEnum
from typing import Any, NotRequired, Protocol, TypedDict


class DebateProtocol(StrEnum):
    """What an advisor sees of the current round.

    ``parallel`` (the default, the final-study protocol): each advisor reads
    only the GM's current proposal and the transcript up to the start of the
    round, so the advisors of one round answer independently, as if in
    parallel. ``sequential`` (the pilot protocol): each advisor also reads the
    suggestions the earlier advisors gave in the same round. The GM review
    sees every suggestion in both protocols.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class Termination(StrEnum):
    """Why the debate loop stopped."""

    GM_STOP = "gm_stop"
    MAX_ROUNDS = "max_rounds"
    # A single player decided without a debate.
    SINGLE_DECISION = "single_decision"


class Suggestion(TypedDict):
    action: str
    reason: str


class LoggedSuggestion(TypedDict):
    """One advisor suggestion kept for turn statistics, never sent to agents."""

    round: int
    advisor: str
    # None when the advisor abstained after exhausting its repairs.
    action: str | None
    # The GM proposal the advisor was answering.
    gm_proposal: str
    abstained: bool


class DebateState(TypedDict):
    context: str
    proposal: str
    initial_proposal: str
    # Current round only, keyed by advisor persona key in speaking order.
    suggestions: dict[str, Suggestion]
    # Every round's suggestions, in speaking order.
    suggestion_log: list[LoggedSuggestion]
    # Recovery steps taken this turn, e.g. "abstained:bold".
    fallbacks: list[str]
    transcript: list[str]
    # Transcript length when the current round's advisors began; a parallel
    # advisor sees only transcript[:round_start].
    round_start: int
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
        "initial_proposal": "",
        "suggestions": {},
        "suggestion_log": [],
        "fallbacks": [],
        "transcript": [],
        "round_start": 0,
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
