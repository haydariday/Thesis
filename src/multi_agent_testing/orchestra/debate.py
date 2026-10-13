import json
import time
from collections.abc import Callable

from ..agent.agent import Agent
from ..agent.backend import Completion
from ..agent.persona_spec import ActionRule
from ..agent.personas import Lineup
from ..decision import AgentDecision
from ..run_log import CallRecorder
from .debate_context import DebateState, NodeFn, Termination
from .flow.sequential import FINALIZE, NEXT_ROUND, build_sequential_graph


def create_debate_graph(
    lineup: Lineup,
    *,
    stream: bool = False,
    validate_action: Callable[[str], str] | None = None,
    max_repairs: int = 1,
    recorder: CallRecorder | None = None,
):
    """Build the debate using validated model decisions."""

    gm = lineup.gm

    def record_call(
        agent: Agent,
        attempt: int,
        *,
        rejected: bool,
        error_type: str | None,
        completion: Completion | None,
        elapsed_seconds: float,
    ) -> None:
        if recorder is None:
            return

        recorder.record(
            role=agent.role.value,
            attempt=attempt,
            rejected=rejected,
            error_type=error_type,
            prompt_tokens=(
                completion.prompt_tokens if completion is not None else None
            ),
            completion_tokens=(
                completion.completion_tokens
                if completion is not None
                else None
            ),
            total_tokens=(
                completion.total_tokens if completion is not None else None
            ),
            elapsed_seconds=elapsed_seconds,
            model=(
                completion.model if completion is not None else None
            ),
        )

    def ask(
        agent: Agent,
        state: DebateState,
        task: str,
        *,
        allow_stop: bool = False,
        action_rule: ActionRule = ActionRule.ANY,
    ) -> AgentDecision:
        payload = {
            "game_context": state["context"],
            "proposal": state["proposal"],
            "suggestions": state["suggestions"],
            "transcript": state["transcript"],
            "completed_rounds": state["round"],
            "task": task,
        }

        def display_chunk(chunk: str) -> None:
            print(chunk, end="", flush=True)

        for attempt in range(max_repairs + 1):
            decision = None
            error: ValueError | None = None
            started = time.perf_counter()

            correction = " | correction" if attempt > 0 else ""

            print(
                f"\nAgent: {agent.name} | "
                f"round {state['round'] + 1}/{state['max_rounds']}"
                f"{correction}"
            )

            try:
                decision = agent.decide(
                    json.dumps(payload, ensure_ascii=False),
                    on_chunk=display_chunk if stream else None,
                )
            except ValueError as exc:
                error = exc
            except Exception as exc:
                if stream:
                    print()

                record_call(
                    agent,
                    attempt + 1,
                    rejected=False,
                    error_type=type(exc).__name__,
                    completion=agent.last_completion,
                    elapsed_seconds=time.perf_counter() - started,
                )
                raise

            if stream:
                print()

            if decision is not None:
                if not stream:
                    print(decision.model_dump_json(indent=2))

                try:
                    if validate_action is not None:
                        decision = decision.model_copy(
                            update={
                                "action": validate_action(
                                    decision.action
                                )
                            }
                        )

                    if decision.stop and (agent is not gm or not allow_stop):
                        raise ValueError(
                            "Only GM review may request a stop."
                        )

                    if (
                        action_rule == ActionRule.MUST_DIFFER
                        and decision.action == state["proposal"]
                    ):
                        raise ValueError(
                            f"{agent.name} must offer a different action."
                        )

                    if (
                        action_rule == ActionRule.MUST_EQUAL
                        and decision.action != state["proposal"]
                    ):
                        raise ValueError(
                            f"{agent.name} must defend the current GM action."
                        )

                except ValueError as exc:
                    error = exc

            record_call(
                agent,
                attempt + 1,
                rejected=error is not None,
                error_type=(
                    type(error).__name__ if error is not None else None
                ),
                completion=agent.last_completion,
                elapsed_seconds=time.perf_counter() - started,
            )

            if error is None:
                if decision is None:
                    raise AssertionError(
                        "A validated decision must be present."
                    )

                return decision

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
            gm,
            state,
            "Propose an initial action. Set stop to false. "
            "The advisors have not spoken yet.",
        )

        return {
            "proposal": decision.action,
            "transcript": state["transcript"] + [
                f"GM proposes {decision.action}: {decision.reason}"
            ],
        }

    def advisor_node(agent: Agent) -> tuple[str, NodeFn]:
        spec = agent.persona

        verb = "defends" if spec.action_rule == ActionRule.MUST_EQUAL else "suggests"

        def node(state: DebateState) -> dict:
            decision = ask(agent, state, spec.task, action_rule=spec.action_rule)

            return {
                "suggestions": {
                    **state["suggestions"],
                    spec.key: {
                        "action": decision.action,
                        "reason": decision.reason,
                    },
                },
                "transcript": state["transcript"] + [
                    f"{agent.name} {verb} {decision.action}: {decision.reason}"
                ],
            }

        return spec.key, node

    def gm_review(state: DebateState) -> dict:
        decision = ask(
            gm,
            state,
            "Review every advisor's suggestion and the full transcript. "
            "Retain or revise the proposal. Set stop to true only if another "
            "round is unlikely to change your decision; otherwise false. "
            "Do not claim unanimous agreement without evidence.",
            allow_stop=True,
        )

        return {
            "proposal": decision.action,
            "suggestions": {},
            "round": state["round"] + 1,
            "stop": decision.stop,
            "transcript": state["transcript"] + [
                f"GM reviews and selects {decision.action}: {decision.reason}"
            ],
        }

    def route_after_review(state: DebateState) -> str:
        if state["stop"] or state["round"] >= state["max_rounds"]:
            return FINALIZE

        return NEXT_ROUND

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
        advisors=[advisor_node(agent) for agent in lineup.advisors],
        gm_review=gm_review,
        finalize=finalize,
        route_after_review=route_after_review,
    )
