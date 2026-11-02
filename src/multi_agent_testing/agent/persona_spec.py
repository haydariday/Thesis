from dataclasses import dataclass
from enum import StrEnum


class Slot(StrEnum):
    """Where a persona sits in the debate."""

    GM = "gm"
    ADVISOR = "advisor"


class ActionRule(StrEnum):
    """How an advisor's action must relate to the GM's current proposal."""

    ANY = "any"
    MUST_DIFFER = "must_differ"
    MUST_EQUAL = "must_equal"


@dataclass(frozen=True)
class PersonaSpec:
    """One persona as data: who it is, what it is told and what it may answer.

    ``instruction`` is the system prompt. ``task`` is the per-turn request an
    advisor receives; the GM's propose and review requests belong to the
    debate graph, so a GM persona leaves it empty.
    """

    key: str
    display_name: str
    slot: Slot
    instruction: str
    task: str = ""
    action_rule: ActionRule = ActionRule.ANY

    def __post_init__(self) -> None:
        if self.slot == Slot.ADVISOR and not self.task:
            raise ValueError(f"Advisor persona {self.key!r} needs a task.")
        if self.slot == Slot.GM and (self.task or self.action_rule != ActionRule.ANY):
            raise ValueError(f"GM persona {self.key!r} takes no task or action rule.")
