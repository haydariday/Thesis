"""Persona registry and presets.

Personas are data (:class:`PersonaSpec`), so a preset or an advisor list picks
the debate line-up without editing the graph. The ``pilot-01`` preset keeps the
exact pilot-01 instructions and tasks, so pilot-01 can still be re-run.

The final study adds two baselines. ``solo`` is a single player with no
advisors (C2), and its line-up is played by a one-decision graph. ``neutral``
pairs the neutral GM with three advisors that share one instruction without a
playstyle (C3).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .agent import Agent
from .agent_role import AgentRole
from .backend import ModelBackend, ScriptedBackend
from .persona_spec import ActionRule, PersonaSpec, Slot

# Final study C3: one instruction without a playstyle, shared by three
# advisor keys so the debate and the statistics can still tell them apart.
# It asks for an improvement, as the persona prompts do, rather than for the
# best guess: the F7 smoke test showed "the best guess" sends the model into
# a solver-like search that runs past max_tokens.
NEUTRAL_ADVISOR_INSTRUCTION = (
    "You are an advisor in a Wordle playtesting system. "
    "Critique the GM's proposal and suggest a better guess if one exists. "
    "If you see no clear improvement, return the proposal unchanged."
)
NEUTRAL_ADVISOR_TASK = (
    "Critique the current GM proposal. "
    "If you see a better guess, suggest it and explain why. "
    "Otherwise return the proposal unchanged. "
    "Set stop to false."
)
NEUTRAL_ADVISOR_KEYS: tuple[str, ...] = ("neutral_1", "neutral_2", "neutral_3")

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
    PersonaSpec(
        key="solo_player",
        display_name="Player",
        slot=Slot.PLAYER,
        instruction=(
            "You are a player in a Wordle playtesting system. "
            "Choose the next guess based on the available game state "
            "and explain your choice briefly. "
            "Do not invent game feedback."
        ),
        task="Choose the next guess and explain why. Set stop to false.",
    ),
    *(
        PersonaSpec(
            key=key,
            display_name=f"Advisor {number}",
            slot=Slot.ADVISOR,
            instruction=NEUTRAL_ADVISOR_INSTRUCTION,
            task=NEUTRAL_ADVISOR_TASK,
        )
        for number, key in enumerate(NEUTRAL_ADVISOR_KEYS, start=1)
    ),
)

PERSONAS: dict[str, PersonaSpec] = {spec.key: spec for spec in _PERSONA_LIST}


@dataclass(frozen=True)
class Preset:
    # The deciding agent: a GM persona, or a player persona when there are
    # no advisors.
    gm: str
    advisors: tuple[str, ...]


PRESETS: dict[str, Preset] = {
    "pilot-01": Preset(gm="neutral_gm_v1", advisors=("negative", "positive")),
    "pilot-02": Preset(gm="neutral_gm", advisors=("bold", "cautious", "casual")),
    "pilot-02-core": Preset(gm="neutral_gm", advisors=("bold", "cautious")),
    "solo": Preset(gm="solo_player", advisors=()),
    "neutral": Preset(gm="neutral_gm", advisors=NEUTRAL_ADVISOR_KEYS),
}


@dataclass(frozen=True)
class Lineup:
    """The GM and the advisors in speaking order.

    A single-agent line-up has no advisors; ``gm`` is then its player.
    """

    gm: Agent
    advisors: tuple[Agent, ...]
    preset: str | None = None

    @property
    def solo(self) -> bool:
        return not self.advisors

    @property
    def agents(self) -> tuple[Agent, ...]:
        return (self.gm, *self.advisors)

    def instructions(self) -> dict[str, str]:
        """System prompt per role, in speaking order, for run metadata."""

        return {agent.role.value: agent.instruction for agent in self.agents}

    def config(self) -> dict[str, Any]:
        """Keys and full persona text, for experiment configs and run metadata."""

        return {
            "preset": self.preset,
            "gm": self.gm.persona.key,
            "advisors": [agent.persona.key for agent in self.advisors],
            "specs": {
                agent.persona.key: {
                    "display_name": agent.persona.display_name,
                    "slot": agent.persona.slot.value,
                    "instruction": agent.persona.instruction,
                    "task": agent.persona.task,
                    "action_rule": agent.persona.action_rule.value,
                }
                for agent in self.agents
            },
        }


def _role_for(spec: PersonaSpec) -> AgentRole:
    # The player decides each turn as the GM does, so its calls log as "gm".
    return AgentRole.GM if spec.slot in (Slot.GM, Slot.PLAYER) else AgentRole(spec.key)


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
    and defaults to ``neutral_gm`` when only ``advisors`` is given. A line-up
    without advisors needs a player persona as its ``gm``, and a player never
    gets advisors.
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

    lead_slot = Slot.GM if advisor_keys else Slot.PLAYER
    if not advisor_keys and gm_key in PERSONAS and PERSONAS[gm_key].slot != Slot.PLAYER:
        raise ValueError("At least one advisor is required.")
    if len(set(advisor_keys)) != len(advisor_keys):
        raise ValueError(f"Advisors must not repeat: {', '.join(advisor_keys)}.")

    if backend is None:
        backend = ScriptedBackend()

    return Lineup(
        gm=build_agent(_lookup(gm_key, lead_slot), backend),
        advisors=tuple(build_agent(_lookup(key, Slot.ADVISOR), backend) for key in advisor_keys),
        preset=preset,
    )


def lineup_from_config(
    block: Mapping[str, Any] | None,
    backend: ModelBackend | None = None,
) -> Lineup:
    """Rebuild a recorded line-up and refuse if the registry text has drifted.

    ``None`` (a config written before personas were recorded) means the
    ``pilot-01`` preset.
    """

    if block is None:
        return create_lineup(backend, preset="pilot-01")

    preset = block.get("preset")
    lineup = create_lineup(
        backend,
        preset=preset,
        gm=block["gm"],
        advisors=None if preset is not None else block["advisors"],
    )
    if lineup.config() != dict(block):
        raise ValueError(
            "The persona registry no longer matches the recorded line-up "
            f"({lineup.gm.persona.key}, {', '.join(block['advisors'])}); "
            "a changed prompt is a new configuration."
        )
    return lineup
