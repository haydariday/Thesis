from .agent.personas import create_lineup
from .orchestra.debate import create_debate_graph
from .orchestra.debate_context import new_debate_state


def main() -> None:
    lineup = create_lineup(preset="pilot-01")
    graph = create_debate_graph(lineup)

    initial_state = new_debate_state(
        (
            "A new Wordle game has started. "
            "There are no previous guesses. "
            "Six attempts remain."
        ),
        max_rounds=1,
    )

    result = graph.invoke(initial_state)

    print("SCRIPTED ORCHESTRATION TEST\n")

    for message in result["transcript"]:
        print(message)
        print()

    print(f"Final action: {result['final_action']}")
    print(f"Completed rounds: {result['round']}")
    print(f"Termination: {result['termination']}")
