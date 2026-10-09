"""Single-game Wordle playthrough shared by the CLI and the experiment runner."""

import time

from .agent.agent import Agent
from .agent.agent_role import AgentRole
from .games.wordle.bridge import WordleBridge
from .games.wordle.engine import WordleGame
from .orchestra.debate import create_debate_graph
from .orchestra.debate_context import DebateState
from .run_log import CallRecorder, RunLog


def play_wordle_game(
    *,
    game: WordleGame,
    bridge: WordleBridge,
    agents: dict[AgentRole, Agent],
    run: RunLog,
    max_rounds: int,
    max_repairs: int,
    stream: bool = False,
    echo: bool = False,
    raise_errors: bool = True,
) -> RunLog:
    """Play one complete Wordle game, checkpointing every turn to ``run``."""

    recorder = CallRecorder()
    started = time.perf_counter()

    def sync_metrics() -> None:
        run.data["calls"] = recorder.as_dicts()
        run.data["counters"] = recorder.counters()
        run.data["token_usage"] = recorder.token_usage()

    try:
        graph = create_debate_graph(
            agents,
            stream=stream,
            validate_action=bridge.validate_action,
            max_repairs=max_repairs,
            recorder=recorder,
        )

        while not game.done:
            observation = game.observation()
            turn = len(observation["history"]) + 1
            turn_started = time.perf_counter()

            if echo:
                print(f"\n{'=' * 40}")
                print(f"Wordle turn {turn}")

            initial_state: DebateState = {
                "context": bridge.observe(),
                "proposal": "",
                "alternative": "",
                "transcript": [],
                "final_action": "",
                "round": 0,
                "max_rounds": max_rounds,
                "stop": False,
            }

            result = graph.invoke(
                initial_state,
                {
                    "recursion_limit": max_rounds * 3 + 5,
                },
            )

            guess_result = bridge.execute(
                result["final_action"]
            )
            termination = result["termination"]

            run.data["turns"].append(
                {
                    "turn": turn,
                    "observation_before": observation,
                    "final_action": guess_result.guess,
                    "feedback": guess_result.feedback,
                    "debate_rounds": result["round"],
                    "gm_requested_stop": result["stop"],
                    "round_cap_reached": (
                        result["round"] >= max_rounds
                    ),
                    "termination": getattr(
                        termination,
                        "value",
                        termination,
                    ),
                    "transcript": result["transcript"],
                    "elapsed_seconds": (
                        time.perf_counter() - turn_started
                    ),
                }
            )

            sync_metrics()
            run.save()

            if echo:
                print(f"\nExecuted guess: {guess_result.guess}")
                print(f"Feedback: {guess_result.feedback}")
                print(f"Debate rounds: {result['round']}")
                print(f"Termination: {termination}")

        run.data["status"] = "completed"

    except KeyboardInterrupt:
        run.data["status"] = "interrupted"
        run.data["error"] = {"type": "KeyboardInterrupt"}
        raise

    except Exception as error:
        run.data["status"] = "failed"
        run.data["error"] = {"type": type(error).__name__}

        if echo:
            print(f"\nRun failed: {type(error).__name__}")

        if raise_errors:
            raise

    finally:
        observation = game.observation()
        guesses_used = len(observation["history"])

        run.data["outcome"] = {
            "game_finished": game.done,
            "won": game.won if game.done else None,
            "guesses_used": guesses_used,
            "solve_guesses": (
                guesses_used if game.won else None
            ),
            "history": observation["history"],
        }
        run.data["elapsed_seconds"] = (
            time.perf_counter() - started
        )

        sync_metrics()
        run.save()

        if echo:
            print(f"\nResult saved: {run.path}")

    return run
