from .agent.personas import create_agents
from .orchestra.debate import DebateState, create_debate_graph


def main() -> None:
    agents = create_agents()
    graph = create_debate_graph(agents)

    initial_state: DebateState = {
        "context": (
            "A new Wordle game has started. "
            "There are no previous guesses. "
            "Six attempts remain."
        ),
        "proposal": "",
        "alternative": "",
        "transcript": [],
        "final_action": "",
        "round": 0,
        "max_rounds": 1,
        "stop": False,
    }

    result = graph.invoke(initial_state)

    print("SCRIPTED ORCHESTRATION TEST\n")

    for message in result["transcript"]:
        print(message)
        print()

    print(f"Final action: {result['final_action']}")
    print(f"Completed rounds: {result['round']}")
    print(f"Termination: {result['termination']}")
