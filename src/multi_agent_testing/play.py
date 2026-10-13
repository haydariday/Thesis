"""Single-game Wordle playthrough shared by the CLI and the experiment runner."""

import time
from collections.abc import Mapping, Sequence
from typing import Any

from .agent.personas import Lineup
from .games.wordle.bridge import WordleBridge
from .games.wordle.candidates import filter_candidates, is_consistent
from .games.wordle.engine import WordleGame
from .orchestra.debate import create_debate_graph
from .orchestra.debate_context import new_debate_state
from .orchestra.flow.sequential import recursion_limit
from .run_log import CallRecorder, RunLog


def turn_statistics(
    result: Mapping[str, Any],
    final_action: str,
    advisor_keys: Sequence[str],
    history: Sequence[Mapping[str, str]],
    candidates: set[str] | None,
) -> dict[str, Any]:
    """GM and persona statistics for one turn (pilot-02 plan, Section 2.3).

    ``history`` is the public feedback before the turn. ``candidates`` is the
    vocabulary filtered by that history, or None without a vocabulary.
    """

    initial = result["initial_proposal"]
    log = result["suggestion_log"]

    suggestions = [
        {
            **entry,
            "agreed": entry["action"] == entry["gm_proposal"],
            "is_candidate": is_consistent(entry["action"], history),
        }
        for entry in log
    ]

    return {
        "initial_proposal": initial,
        "gm_retained": final_action == initial,
        "advisor_suggestions": suggestions,
        # Advisors whose word the GM switched to; empty if the GM kept its own.
        "adopted_from": [
            key
            for key in advisor_keys
            if final_action != initial
            and any(
                entry["advisor"] == key and entry["action"] == final_action
                for entry in log
            )
        ],
        # True when the advisor returned the GM's proposal in every round.
        "advisor_agreed": {
            key: all(
                entry["agreed"]
                for entry in suggestions
                if entry["advisor"] == key
            )
            for key in advisor_keys
        },
        "is_candidate": {
            "initial_proposal": is_consistent(initial, history),
            "final_action": is_consistent(final_action, history),
        },
        "candidates_remaining": (
            len(candidates) if candidates is not None else None
        ),
    }


def play_wordle_game(
    *,
    game: WordleGame,
    bridge: WordleBridge,
    lineup: Lineup,
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
    advisor_keys = [agent.persona.key for agent in lineup.advisors]
    # Narrowed by public feedback each turn; the answer is never consulted.
    candidates = (
        set(game.vocabulary) if game.vocabulary is not None else None
    )

    def sync_metrics() -> None:
        run.data["calls"] = recorder.as_dicts()
        run.data["counters"] = recorder.counters()
        run.data["token_usage"] = recorder.token_usage()

    try:
        graph = create_debate_graph(
            lineup,
            stream=stream,
            validate_action=bridge.validate_action,
            max_repairs=max_repairs,
            recorder=recorder,
        )

        while not game.done:
            observation = game.observation()
            turn = len(observation["history"]) + 1
            if candidates is not None:
                candidates = filter_candidates(
                    candidates, observation["history"]
                )
            turn_started = time.perf_counter()

            if echo:
                print(f"\n{'=' * 40}")
                print(f"Wordle turn {turn}")

            result = graph.invoke(
                new_debate_state(bridge.observe(), max_rounds),
                {
                    "recursion_limit": recursion_limit(
                        max_rounds, len(lineup.advisors)
                    ),
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
                    **turn_statistics(
                        result,
                        guess_result.guess,
                        advisor_keys,
                        observation["history"],
                        candidates,
                    ),
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
