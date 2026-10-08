from .agent import Agent
from .agent_role import AgentRole
from .backend import ModelBackend, ScriptedBackend


def create_agents(
    backend: ModelBackend | None = None,
) -> dict[AgentRole, Agent]:
    """Create the three personas with a shared model backend."""

    if backend is None:
        backend = ScriptedBackend()

    gm = Agent(
        name="Game Master",
        backend=backend,
        role=AgentRole.GM,
        instruction=(
            "You are the GM in a Wordle playtesting system. "
            "Propose a guess based on the available game state. "
            "After the advisors respond, evaluate both arguments "
            "and retain or revise your proposal. "
            "Do not invent game feedback or claim unanimous agreement."
        ),
    )

    negative = Agent(
        backend=backend,
        name="Negative Advisor",
        role=AgentRole.NEGATIVE,
        instruction=(
            "You are the Negative advisor in a Wordle playtesting system. "
            "Challenge the GM's current proposed guess. "
            "Identify a specific weakness and suggest an alternative "
            "with supporting reasoning. "
            "Your goal is to improve the decision, not to lose the game."
        ),
    )

    positive = Agent(
        backend=backend,
        name="Positive Advisor",
        role=AgentRole.POSITIVE,
        instruction=(
            "You are the Positive advisor in a Wordle playtesting system. "
            "Respond to the Negative advisor's critique. "
            "Defend the GM's current proposed guess by explaining "
            "its strengths and the alternative's trade-offs. "
            "Acknowledge valid weaknesses instead of inventing a defense."
        ),
    )

    return {
        AgentRole.GM: gm,
        AgentRole.NEGATIVE: negative,
        AgentRole.POSITIVE: positive,
    }
