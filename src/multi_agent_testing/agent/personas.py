"""Persona registry and presets.

Personas are data (:class:`PersonaSpec`), so a preset or an advisor list picks
the debate line-up without editing the graph. The ``pilot-01`` preset keeps the
exact pilot-01 instructions and tasks, so pilot-01 can still be re-run.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .agent import Agent
from .agent_role import AgentRole
from .backend import ModelBackend, ScriptedBackend
from .persona_spec import ActionRule, PersonaSpec, Slot

_PERSONA_LIST: tuple[PersonaSpec, ...] = (
    PersonaSpec(
        key="neutral_gm_v1",
        display_name="Game Master",
        slot=Slot.GM,
        instruction=(
            "You are the GM in a Wordle playtesting system. "
            "Propose a guess based on the available game state. "
            "After the advisors respond, evaluate both arguments "
            "and retain or revise your proposal. "
            "Do not invent game feedback or claim unanimous agreement."
        ),
    ),
    PersonaSpec(
        key="neutral_gm",
        display_name="Game Master",
        slot=Slot.GM,
        instruction=(
            "You are the GM in a Wordle playtesting system. "
            "Propose a guess based on the available game state. "
            "After the advisors respond, evaluate every advisor's argument "
            "and retain or revise your proposal. "
            "Do not invent game feedback or claim unanimous agreement."
        ),
    ),
    PersonaSpec(
        key="negative",
        display_name="Negative Advisor",
        slot=Slot.ADVISOR,
        instruction=(
            "You are the Negative advisor in a Wordle playtesting system. "
            "Challenge the GM's current proposed guess. "
            "Identify a specific weakness and suggest an alternative "
            "with supporting reasoning. "
            "Your goal is to improve the decision, not to lose the game."
        ),
        task=(
            "Challenge the current GM proposal. Propose a different "
            "action and explain why it may be better. Set stop to false."
        ),
        action_rule=ActionRule.MUST_DIFFER,
    ),
    PersonaSpec(
        key="positive",
        display_name="Positive Advisor",
        slot=Slot.ADVISOR,
        instruction=(
            "You are the Positive advisor in a Wordle playtesting system. "
            "Respond to the Negative advisor's critique. "
            "Defend the GM's current proposed guess by explaining "
            "its strengths and the alternative's trade-offs. "
            "Acknowledge valid weaknesses instead of inventing a defense."
        ),
        task=(
            "Counter the latest Negative critique and defend the current "
            "GM proposal. Your action must equal the proposal exactly. "
            "Acknowledge valid limitations. Set stop to false."
        ),
        action_rule=ActionRule.MUST_EQUAL,
    ),
    PersonaSpec(
        key="bold",
        display_name="Bold Advisor",
        slot=Slot.ADVISOR,
        instruction=(
            "You are the Bold advisor in a Wordle playtesting system. "
            "You prefer guesses that could still be the answer, "
            "so the game can be won as early as possible. "
            "Critique the GM's proposal from this view and suggest "
            "a better candidate answer if one exists. "
            "Accept the risk of using more guesses later."
        ),
        task=(
            "Critique the current GM proposal from the Bold view. "
            "Suggest a guess that could still be the answer and explain why. "
            "If the proposal is already the best such guess, return it unchanged. "
            "Set stop to false."
        ),
    ),
    PersonaSpec(
        key="cautious",
        display_name="Cautious Advisor",
        slot=Slot.ADVISOR,
        instruction=(
            "You are the Cautious advisor in a Wordle playtesting system. "
            "You prefer guesses that rule out the most remaining letters, "
            "even if the guess cannot be the answer. "
            "Critique the GM's proposal from this view and suggest "
            "a more informative guess if one exists. "
            "Your priority is never losing the game."
        ),
        task=(
            "Critique the current GM proposal from the Cautious view. "
            "Suggest the guess that rules out the most remaining letters "
            "and explain why, even if it cannot be the answer. "
            "If the proposal is already the most informative guess, return it unchanged. "
            "Set stop to false."
        ),
    ),
    PersonaSpec(
        key="casual",
        display_name="Casual Advisor",
        slot=Slot.ADVISOR,
        instruction=(
            "You are the Casual advisor in a Wordle playtesting system. "
            "You play like a typical daily player. "
            "You prefer common, familiar words and a habitual opening word. "
            "You do not compute letter statistics. "
            "Critique the GM's proposal from this view and suggest "
            "the guess an everyday player would make."
        ),
        task=(
            "Respond to the current GM proposal as an everyday player. "
            "Suggest the guess you would make and explain why in plain terms. "
            "If you would play the proposal too, return it unchanged. "
            "Set stop to false."
        ),
    ),
)

PERSONAS: dict[str, PersonaSpec] = {spec.key: spec for spec in _PERSONA_LIST}


@dataclass(frozen=True)
class Preset:
    gm: str
    advisors: tuple[str, ...]


PRESETS: dict[str, Preset] = {
    "pilot-01": Preset(gm="neutral_gm_v1", advisors=("negative", "positive")),
    "pilot-02": Preset(gm="neutral_gm", advisors=("bold", "cautious", "casual")),
    "pilot-02-core": Preset(gm="neutral_gm", advisors=("bold", "cautious")),
}


@dataclass(frozen=True)
class Lineup:
    """The GM and the advisors in speaking order."""

    gm: Agent
    advisors: tuple[Agent, ...]
    preset: str | None = None

    @property
    def agents(self) -> tuple[Agent, ...]:
        return (self.gm, *self.advisors)

    def instructions(self) -> dict[str, str]:
        """System prompt per role, in speaking order, for run metadata."""

        return {agent.role.value: agent.instruction for agent in self.agents}


def _role_for(spec: PersonaSpec) -> AgentRole:
    return AgentRole.GM if spec.slot == Slot.GM else AgentRole(spec.key)


def _lookup(key: str, slot: Slot) -> PersonaSpec:
    spec = PERSONAS.get(key)
    if spec is None:
        raise ValueError(f"Unknown persona {key!r}. Known: {', '.join(PERSONAS)}.")
    if spec.slot != slot:
        raise ValueError(f"Persona {key!r} is a {spec.slot} persona, not {slot}.")
    return spec


def build_agent(spec: PersonaSpec, backend: ModelBackend) -> Agent:
    return Agent(
        name=spec.display_name,
        role=_role_for(spec),
        instruction=spec.instruction,
        backend=backend,
        persona=spec,
    )


def create_lineup(
    backend: ModelBackend | None = None,
    *,
    preset: str | None = None,
    gm: str | None = None,
    advisors: Sequence[str] | None = None,
) -> Lineup:
    """Build the GM and ordered advisors from a preset or explicit keys.

    Give either ``preset`` or ``advisors``. ``gm`` overrides the preset's GM
    and defaults to ``neutral_gm`` when only ``advisors`` is given.
    """

    if (preset is None) == (advisors is None):
        raise ValueError("Give exactly one of preset or advisors.")

    if preset is not None:
        chosen = PRESETS.get(preset)
        if chosen is None:
            raise ValueError(f"Unknown preset {preset!r}. Known: {', '.join(PRESETS)}.")
        gm_key = gm or chosen.gm
        advisor_keys = chosen.advisors
    else:
        gm_key = gm or "neutral_gm"
        advisor_keys = tuple(advisors or ())

    if not advisor_keys:
        raise ValueError("At least one advisor is required.")
    if len(set(advisor_keys)) != len(advisor_keys):
        raise ValueError(f"Advisors must not repeat: {', '.join(advisor_keys)}.")

    if backend is None:
        backend = ScriptedBackend()

    return Lineup(
        gm=build_agent(_lookup(gm_key, Slot.GM), backend),
        advisors=tuple(build_agent(_lookup(key, Slot.ADVISOR), backend) for key in advisor_keys),
        preset=preset,
    )

