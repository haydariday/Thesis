"""Graph topology for the sequential Wordle debate flow.

Owns the node names, edges and compilation. Node behaviour and the routing
policy are injected by the caller, so this module stays free of agent logic.
"""

from langgraph.graph import END, START, StateGraph

from ..debate_context import DebateState, NodeFn, RouterFn

PROPOSE = "gm_propose"
CHALLENGE = "negative_challenge"
DEFEND = "positive_defend"
REVIEW = "gm_review"
FINALIZE = "finalize"

def build_sequential_graph(
    *,
    gm_propose: NodeFn,
    negative_challenge: NodeFn,
    positive_defend: NodeFn,
    gm_review: NodeFn,
    finalize: NodeFn,
    route_after_review: RouterFn,
):
    """Wire the fixed propose -> challenge -> defend -> review loop."""

    builder = StateGraph(DebateState)

    builder.add_node(PROPOSE, gm_propose)
    builder.add_node(CHALLENGE, negative_challenge)
    builder.add_node(DEFEND, positive_defend)
    builder.add_node(REVIEW, gm_review)
    builder.add_node(FINALIZE, finalize)

    builder.add_edge(START, PROPOSE)
    builder.add_edge(PROPOSE, CHALLENGE)
    builder.add_edge(CHALLENGE, DEFEND)
    builder.add_edge(DEFEND, REVIEW)
    builder.add_conditional_edges(
        REVIEW,
        route_after_review,
        {CHALLENGE: CHALLENGE, FINALIZE: FINALIZE},
    )
    builder.add_edge(FINALIZE, END)

    return builder.compile()
