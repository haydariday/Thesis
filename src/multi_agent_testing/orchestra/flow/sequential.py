"""Graph topology for the sequential Wordle debate flow.

Owns the node names, edges and compilation. Node behaviour and the routing
policy are injected by the caller, so this module stays free of agent logic.
"""

from collections.abc import Sequence

from langgraph.graph import END, START, StateGraph

from ..debate_context import DebateState, NodeFn, RouterFn

PROPOSE = "gm_propose"
REVIEW = "gm_review"
FINALIZE = "finalize"
# Router result that starts another round at the first advisor.
NEXT_ROUND = "next_round"


def advisor_node_name(key: str) -> str:
    return f"advisor_{key}"


def recursion_limit(max_rounds: int, advisor_count: int) -> int:
    """LangGraph step budget: each round runs every advisor plus the review."""

    return max_rounds * (advisor_count + 1) + 5


def build_sequential_graph(
    *,
    gm_propose: NodeFn,
    advisors: Sequence[tuple[str, NodeFn]],
    gm_review: NodeFn,
    finalize: NodeFn,
    route_after_review: RouterFn,
):
    """Wire propose -> advisor_1 -> ... -> advisor_n -> review, then loop or finalize.

    ``advisors`` is an ordered list of ``(persona_key, node)`` pairs.
    ``route_after_review`` returns :data:`NEXT_ROUND` or :data:`FINALIZE`.
    """

    if not advisors:
        raise ValueError("The debate needs at least one advisor.")

    names = [advisor_node_name(key) for key, _ in advisors]
    if len(set(names)) != len(names):
        raise ValueError("Advisor keys must be unique.")

    builder = StateGraph(DebateState)

    builder.add_node(PROPOSE, gm_propose)
    for name, (_, node) in zip(names, advisors):
        builder.add_node(name, node)
    builder.add_node(REVIEW, gm_review)
    builder.add_node(FINALIZE, finalize)

    builder.add_edge(START, PROPOSE)
    for source, target in zip([PROPOSE, *names], [*names, REVIEW]):
        builder.add_edge(source, target)
    builder.add_conditional_edges(
        REVIEW,
        route_after_review,
        {NEXT_ROUND: names[0], FINALIZE: FINALIZE},
    )
    builder.add_edge(FINALIZE, END)

    return builder.compile()
