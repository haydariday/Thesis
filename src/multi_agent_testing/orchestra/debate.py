import json
from collections.abc import Callable

from ..agent.agent import Agent
from ..agent.agent_role import AgentRole
from .debate_context import DebateState, Termination
from .flow.sequential import CHALLENGE, FINALIZE, build_sequential_graph


def create_debate_graph(
    agents: dict[AgentRole, Agent],
    *,
    stream: bool = False,
    validate_action: Callable[[str], str] | None = None,
    max_repairs: int = 1,
):
    """Build the debate using validated model decisions."""

    def ask(
        role: AgentRole,
        state: DebateState,
        task: str,
        *,
        allow_stop: bool = False,
    ):
        agent = agents[role]

        payload = {
            "game_context": state["context"],
            "proposal": state["proposal"],
            "alternative": state["alternative"],
            "transcript": state["transcript"],
            "completed_rounds": state["round"],
            "task": task,
        }

        def display_chunk(chunk: str) -> None:
            print(chunk, end="", flush=True)

        for attempt in range(max_repairs + 1):
            decision = None

            print(
                f"\nAgent: {agent.name} | attempt {attempt + 1}"
            )

            try:
                decision = agent.decide(
                    json.dumps(payload, ensure_ascii=False),
                    on_chunk=display_chunk if stream else None,
                )

                if stream:
                    print()
                else:
                    print(decision.model_dump_json(indent=2))

                if validate_action is not None:
                    decision = decision.model_copy(
                        update={
                            "action": validate_action(decision.action)
                        }
                    )

                if decision.stop and (
                    role != AgentRole.GM or not allow_stop
                ):
                    raise ValueError(
                        "Only GM review may request a stop."
                    )

                if (
                    role == AgentRole.NEGATIVE
                    and decision.action == state["proposal"]
                ):
                    raise ValueError(
                        "Negative must offer a different action."
                    )

                if (
                    role == AgentRole.POSITIVE
                    and decision.action != state["proposal"]
                ):
                    raise ValueError(
                        "Positive must defend the current GM action."
                    )

                return decision

            except ValueError as error:
                if stream and decision is None:
                    print()

                print(f"Rejected response: {error}")

                if attempt == max_repairs:
                    raise ValueError(
                        f"{agent.name} failed validation after "
                        f"{max_repairs + 1} attempt(s): {error}"
                    ) from error

                payload["repair"] = {
                    "validation_error": str(error),
                    "previous_decision": (
                        decision.model_dump()
                        if decision is not None
                        else None
                    ),
                    "instruction": (
                        "Correct the response using this error "
                        "and the game rules. "
                        "Return only the required JSON. "
                        "Keep your assigned role. "
                        "This is a correction within the same turn, "
                        "not a new round."
                    ),
                }

        raise AssertionError("Unreachable")

    def gm_propose(state: DebateState) -> dict:
        decision = ask(
            AgentRole.GM,
            state,
            "Propose an initial action. Set stop to false. "
            "The advisors have not spoken yet.",
        )

        if decision.stop:
            raise ValueError(
                "GM proposal cannot stop before advisor review."
            )

        return {
            "proposal": decision.action,
            "transcript": state["transcript"] + [
                f"GM proposes {decision.action}: {decision.reason}"
            ],
        }

    def negative_challenge(state: DebateState) -> dict:
        decision = ask(
            AgentRole.NEGATIVE,
            state,
            "Challenge the current GM proposal. Propose a different "
            "action and explain why it may be better. Set stop to false.",
        )

        if decision.stop:
            raise ValueError("Negative cannot stop the debate.")

        if decision.action == state["proposal"]:
            raise ValueError(
                "Negative must offer a different action."
            )

        return {
            "alternative": decision.action,
            "transcript": state["transcript"] + [
                f"Negative suggests {decision.action}: {decision.reason}"
            ],
        }

    def positive_defend(state: DebateState) -> dict:
        decision = ask(
            AgentRole.POSITIVE,
            state,
            "Counter the latest Negative critique and defend the current "
            "GM proposal. Your action must equal the proposal exactly. "
            "Acknowledge valid limitations. Set stop to false.",
        )

        if decision.stop:
            raise ValueError("Positive cannot stop the debate.")

        if decision.action != state["proposal"]:
            raise ValueError(
                "Positive must defend the current GM action."
            )

        return {
            "transcript": state["transcript"] + [
                f"Positive defends {decision.action}: {decision.reason}"
            ],
        }

    def gm_review(state: DebateState) -> dict:
        decision = ask(
            AgentRole.GM,
            state,
            "Review both advisors and the full transcript. Retain or "
            "revise the proposal. Set stop to true only if another "
            "round is unlikely to change your decision; otherwise false. "
            "Do not claim unanimous agreement without evidence.",
            allow_stop=True,
        )

        return {
            "proposal": decision.action,
            "round": state["round"] + 1,
            "stop": decision.stop,
            "transcript": state["transcript"] + [
                f"GM reviews and selects {decision.action}: {decision.reason}"
            ],
        }

    def route_after_review(state: DebateState) -> str:
        if state["stop"] or state["round"] >= state["max_rounds"]:
            return FINALIZE

        return CHALLENGE

    def finalize(state: DebateState) -> dict:
        return {
            "final_action": state["proposal"],
            "termination": (
                Termination.GM_STOP
                if state["stop"]
                else Termination.MAX_ROUNDS
            ),
        }

    return build_sequential_graph(
        gm_propose=gm_propose,
        negative_challenge=negative_challenge,
        positive_defend=positive_defend,
        gm_review=gm_review,
        finalize=finalize,
        route_after_review=route_after_review,
    )
