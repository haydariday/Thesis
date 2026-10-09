"""Compile run JSON checkpoints into an analysis-ready summary table."""

import csv
import json
from pathlib import Path


SUMMARY_FIELDS = [
    "run_id",
    "run_file",
    "puzzle_id",
    "repetition",
    "attempt",
    "status",
    "won",
    "guesses_used",
    "penalized_score",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "elapsed_seconds",
    "turns",
    "gm_stop_turns",
    "max_rounds_turns",
    "error_type",
    "agent_calls",
    "rejected_responses",
    "backend_errors",
]


def summarize_run(run: dict, run_file: str) -> dict:
    """Flatten one run checkpoint into a summary row."""

    metadata = run.get("metadata") or {}
    outcome = run.get("outcome") or {}
    counters = run.get("counters") or {}
    usage = run.get("token_usage") or {}
    error = run.get("error") or {}

    turns = run.get("turns") or []
    gm_stop_turns = sum(
        1
        for turn in turns
        if str(turn.get("termination")) == "gm_stop"
    )
    max_rounds_turns = sum(
        1
        for turn in turns
        if str(turn.get("termination")) == "max_rounds"
    )

    game_finished = bool(outcome.get("game_finished"))
    won = outcome.get("won")
    guesses_used = outcome.get("guesses_used")

    if game_finished and won is True:
        penalized_score = guesses_used
    elif game_finished and won is False:
        penalized_score = 7
    else:
        penalized_score = None

    return {
        "run_id": run.get("run_id"),
        "run_file": run_file,
        "puzzle_id": metadata.get("puzzle_id"),
        "repetition": metadata.get("repetition") or 1,
        "attempt": metadata.get("attempt") or 1,
        "status": run.get("status"),
        "won": won,
        "guesses_used": guesses_used,
        "penalized_score": penalized_score,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "elapsed_seconds": run.get("elapsed_seconds"),
        "turns": len(turns),
        "gm_stop_turns": gm_stop_turns,
        "max_rounds_turns": max_rounds_turns,
        "error_type": error.get("type"),
        "agent_calls": counters.get("agent_calls"),
        "rejected_responses": counters.get("rejected_responses"),
        "backend_errors": counters.get("backend_errors"),
    }


def collect_runs(runs_dir: Path) -> list[dict]:
    """Load every run checkpoint in a directory, sorted by plan order."""

    rows: list[dict] = []

    for path in sorted(runs_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as file:
                run = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        rows.append(summarize_run(run, path.name))

    def sort_key(row: dict) -> tuple:
        puzzle = str(row.get("puzzle_id") or "")
        puzzle_key = int(puzzle) if puzzle.isdecimal() else -1

        return (
            puzzle_key,
            puzzle,
            int(row.get("repetition") or 0),
            int(row.get("attempt") or 0),
        )

    rows.sort(key=sort_key)
    return rows


def write_summary(runs_dir: Path, output_path: Path) -> list[dict]:
    """Regenerate the summary CSV from the run checkpoints."""

    rows = collect_runs(runs_dir)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return rows
