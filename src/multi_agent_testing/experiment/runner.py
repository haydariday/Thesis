"""Resumable experiment runner for the Wordle debate playtesting study.

The runner executes a frozen plan of puzzles by repetitions, calling the
same game and debate components as the CLI entry point. Every execution
attempt is stored as its own run JSON, and an analysis-ready
``run_summary.csv`` is compiled after every attempt.

Stop mid-experiment at any time (Ctrl-C, ``--max-runs`` or
``--max-seconds``); rerun with the ``resume`` subcommand to continue
without touching completed attempts.
"""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from importlib import metadata as importlib_metadata
from pathlib import Path

from dotenv import load_dotenv

from ..agent.backend import ChatCompletionsBackend, ResponsesBackend
from ..agent.persona_args import add_persona_arguments, lineup_from_args
from ..agent.personas import lineup_from_config
from ..agent.providers import (
    PROVIDERS,
    THINKING_MODES,
    default_api_key_env,
    endpoint_error,
    extra_body,
    peak_wait_seconds,
    request_options_error,
    settings_error,
)
from ..games.wordle.bridge import WordleBridge
from ..games.wordle.dataset import (
    WordlePuzzle,
    load_allowed_guesses,
    load_puzzle,
)
from ..games.wordle.engine import WordleGame
from ..play import play_wordle_game
from ..run_log import RunLog
from .summary import write_summary

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# A game takes about a minute, so do not start one this close to a peak window.
PEAK_MARGIN_SECONDS = 180.0


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    return result.stdout.strip() or None


def code_dirty() -> bool | None:
    """True when tracked code, data or dependency files differ from HEAD.

    Untracked files are ignored, since experiment outputs land inside the
    repository while a run is in progress.
    """

    try:
        result = subprocess.run(
            [
                "git", "status", "--porcelain", "--untracked-files=no",
                "--", "src", "pyproject.toml", "uv.lock",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    return bool(result.stdout.strip())


def environment_info() -> dict:
    packages = {}

    for name in ("langgraph", "openai", "pydantic"):
        try:
            packages[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            packages[name] = None

    return {
        "python": sys.version.split()[0],
        "packages": packages,
    }


def source_hash() -> str:
    digest = hashlib.sha256()
    source_root = PROJECT_ROOT / "src" / "multi_agent_testing"

    for path in sorted(source_root.rglob("*.py")):
        digest.update(
            path.relative_to(PROJECT_ROOT).as_posix().encode()
        )
        digest.update(path.read_bytes())

    return digest.hexdigest()


def load_manifest(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows or "puzzle_id" not in rows[0]:
        raise ValueError("Manifest must contain a puzzle_id column.")

    for row in rows:
        puzzle_id = str(row["puzzle_id"])

        if not puzzle_id.isascii() or not puzzle_id.isdecimal():
            raise ValueError(
                f"Manifest puzzle_id {puzzle_id!r} is not numeric."
            )

    return rows


def build_config(args) -> dict:
    dataset = args.dataset.resolve()
    guess_list = args.guess_list.resolve()
    manifest = args.manifest.resolve()

    puzzle_ids = [
        str(row["puzzle_id"]) for row in load_manifest(manifest)
    ]

    if args.limit is not None:
        puzzle_ids = puzzle_ids[: args.limit]

    settings = {
        "backend": args.backend,
        "protocol": args.protocol,
        "model": args.model,
        "base_url": args.base_url,
        "temperature": args.temperature,
        "thinking": args.thinking,
        "max_tokens": args.max_tokens,
        "json_mode": args.json_mode,
        "stream": False,
        "max_rounds": args.max_rounds,
        "max_repairs": args.max_repairs,
        "request_timeout": args.request_timeout,
        "api_retries": args.api_retries,
        "repetitions": args.repetitions,
        "max_attempts_per_unit": args.max_attempts,
        "api_key_env": args.api_key_env or default_api_key_env(args.backend),
    }

    return {
        "experiment_id": args.name or args.experiment_dir.resolve().name,
        "created_at": datetime.now(UTC).isoformat(),
        "settings": settings,
        "dataset": str(dataset),
        "guess_list": str(guess_list),
        "dataset_sha256": file_hash(dataset),
        "guess_list_sha256": file_hash(guess_list),
        "manifest_source": str(manifest),
        "selected_puzzle_ids": puzzle_ids,
        "limit": args.limit,
        "primary_threshold": 4.0,
        "thresholds": [3.8, 4.0, 4.2],
        "code_revision": code_revision(),
        "code_dirty": code_dirty(),
        "source_sha256": source_hash(),
        "environment": environment_info(),
    }


def build_backend(
    settings: dict,
) -> ChatCompletionsBackend | ResponsesBackend:
    api_key_env = settings.get("api_key_env") or "OPENCODE_API_KEY"

    if settings["backend"] in PROVIDERS:
        api_key = os.environ.get(api_key_env, "").strip()

        if not api_key:
            raise SystemExit(
                f"Set {api_key_env} in the environment or .env "
                "before running."
            )
    else:
        api_key = "ollama"

    if settings.get("protocol", "chat") == "responses":
        return ResponsesBackend(
            model=settings["model"],
            base_url=settings["base_url"],
            api_key=api_key,
            temperature=settings.get("temperature"),
            request_timeout=settings["request_timeout"],
            api_retries=settings["api_retries"],
        )

    return ChatCompletionsBackend(
        model=settings["model"],
        base_url=settings["base_url"],
        temperature=settings["temperature"],
        api_key=api_key,
        request_timeout=settings["request_timeout"],
        api_retries=settings["api_retries"],
        extra_body=extra_body(settings.get("thinking")),
        max_tokens=settings.get("max_tokens"),
        json_mode=settings.get("json_mode", False),
    )


def scan_attempts(runs_dir: Path) -> dict[tuple[str, int], list[dict]]:
    """Map each (puzzle, repetition) unit to its recorded attempts."""

    attempts: dict[tuple[str, int], list[dict]] = {}

    for path in sorted(runs_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as file:
                run = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        metadata = run.get("metadata") or {}
        puzzle_id = metadata.get("puzzle_id")
        repetition = metadata.get("repetition")
        attempt = metadata.get("attempt")

        if puzzle_id is None or repetition is None or attempt is None:
            continue

        attempts.setdefault(
            (str(puzzle_id), int(repetition)), []
        ).append(
            {
                "attempt": int(attempt),
                "status": run.get("status"),
                "won": (run.get("outcome") or {}).get("won"),
                "file": path.name,
            }
        )

    for records in attempts.values():
        records.sort(key=lambda record: record["attempt"])

    return attempts


def validate_start_args(parser, args) -> None:
    if not args.model or not args.base_url:
        parser.error("--model and --base-url are required.")

    error = settings_error(
        args.backend, args.protocol, args.temperature, args.thinking
    ) or endpoint_error(args.backend, args.base_url) or request_options_error(
        args.protocol, args.max_tokens, args.json_mode
    )
    if error is not None:
        parser.error(error)

    if args.max_rounds < 1 or args.max_rounds > 10:
        parser.error("--max-rounds must be between 1 and 10.")

    if args.max_repairs < 0 or args.max_repairs > 2:
        parser.error("--max-repairs must be between 0 and 2.")

    if args.request_timeout <= 0:
        parser.error("--request-timeout must be positive.")

    if args.api_retries < 0 or args.api_retries > 2:
        parser.error("--api-retries must be between 0 and 2.")

    if args.repetitions < 1:
        parser.error("--repetitions must be positive.")

    if args.max_attempts < 1 or args.max_attempts > 5:
        parser.error("--max-attempts must be between 1 and 5.")

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive.")


def execute_plan(
    experiment_dir: Path,
    config: dict,
    *,
    max_runs: int | None = None,
    max_seconds: float | None = None,
    allow_peak: bool = False,
) -> None:
    settings = config["settings"]
    runs_dir = experiment_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    summary_path = experiment_dir / "run_summary.csv"
    ledger_path = experiment_dir / "attempts.jsonl"

    backend = build_backend(settings)
    allowed_guesses = load_allowed_guesses(Path(config["guess_list"]))

    puzzle_cache: dict[str, WordlePuzzle] = {}
    attempts = scan_attempts(runs_dir)

    units = [
        (puzzle_id, repetition)
        for puzzle_id in config["selected_puzzle_ids"]
        for repetition in range(1, settings["repetitions"] + 1)
    ]

    print(
        f"Experiment {config['experiment_id']}: "
        f"{len(config['selected_puzzle_ids'])} puzzles x "
        f"{settings['repetitions']} repetitions = "
        f"{len(units)} planned games"
    )

    started_at = time.perf_counter()
    paused_seconds = 0.0
    runs_done = 0
    completed_runs = 0

    try:
        for index, (puzzle_id, repetition) in enumerate(units, start=1):
            if max_runs is not None and runs_done >= max_runs:
                print(f"Stopping after {runs_done} executed attempt(s).")
                break

            if (
                max_seconds is not None
                and runs_done > 0
                and time.perf_counter() - started_at - paused_seconds >= max_seconds
            ):
                print(
                    f"Stopping after {max_seconds:.0f} seconds of work."
                )
                break

            records = attempts.get((puzzle_id, repetition), [])

            if any(
                record["status"] == "completed" for record in records
            ):
                continue

            if len(records) >= settings["max_attempts_per_unit"]:
                print(
                    f"[{index}/{len(units)}] puzzle {puzzle_id} rep "
                    f"{repetition}: replacements exhausted, skipped"
                )
                continue

            attempt = records[-1]["attempt"] + 1 if records else 1
            run_path = runs_dir / (
                f"puzzle-{puzzle_id}-rep{repetition}"
                f"-attempt{attempt}.json"
            )

            if run_path.exists():
                print(
                    f"[{index}/{len(units)}] puzzle {puzzle_id} rep "
                    f"{repetition}: stale attempt file exists, skipped"
                )
                continue

            if not allow_peak:
                wait = peak_wait_seconds(
                    settings["backend"], _utcnow(), PEAK_MARGIN_SECONDS
                )
                if wait > 0:
                    until = _utcnow() + timedelta(seconds=wait)
                    print(
                        f"Peak-price hours for {settings['backend']}: pausing "
                        f"until {until:%Y-%m-%d %H:%M} UTC. Ctrl-C is safe; "
                        "resume later."
                    )
                    _sleep(wait)
                    paused_seconds += wait

            if puzzle_id not in puzzle_cache:
                puzzle_cache[puzzle_id] = load_puzzle(
                    path=Path(config["dataset"]),
                    puzzle_id=puzzle_id,
                )

            puzzle = puzzle_cache[puzzle_id]
            game = WordleGame(
                puzzle,
                allowed_guesses=allowed_guesses,
            )
            bridge = WordleBridge(game)
            lineup = lineup_from_config(settings.get("personas"), backend)

            metadata = {
                "experiment_id": config["experiment_id"],
                "backend": settings["backend"],
                "protocol": settings.get("protocol", "chat"),
                "model_requested": settings["model"],
                "base_url": settings["base_url"],
                "temperature": settings["temperature"],
                "thinking": settings.get("thinking"),
                "max_tokens": settings.get("max_tokens"),
                "json_mode": settings.get("json_mode", False),
                "stream": settings["stream"],
                "max_rounds": settings["max_rounds"],
                "max_repairs": settings["max_repairs"],
                "request_timeout": settings["request_timeout"],
                "api_retries": settings["api_retries"],
                "puzzle_id": puzzle.puzzle_id,
                "target_answer": puzzle.answer,
                "guess_policy": game.observation()["guess_policy"],
                "vocabulary_size": len(allowed_guesses),
                "dataset_sha256": config["dataset_sha256"],
                "guess_list_sha256": config["guess_list_sha256"],
                "repetition": repetition,
                "attempt": attempt,
                "agent_instructions": lineup.instructions(),
                "personas": lineup.config(),
            }

            run = RunLog(metadata=metadata, path=run_path)
            run_started = time.perf_counter()

            play_wordle_game(
                game=game,
                bridge=bridge,
                lineup=lineup,
                run=run,
                max_rounds=settings["max_rounds"],
                max_repairs=settings["max_repairs"],
                stream=False,
                echo=False,
                raise_errors=False,
            )

            elapsed = time.perf_counter() - run_started
            status = run.data["status"]
            outcome = run.data.get("outcome") or {}
            error = run.data.get("error") or {}

            with ledger_path.open("a", encoding="utf-8") as file:
                file.write(
                    json.dumps(
                        {
                            "timestamp": datetime.now(
                                UTC
                            ).isoformat(),
                            "experiment_id": config["experiment_id"],
                            "puzzle_id": puzzle_id,
                            "repetition": repetition,
                            "attempt": attempt,
                            "status": status,
                            "won": outcome.get("won"),
                            "guesses_used": outcome.get("guesses_used"),
                            "elapsed_seconds": round(elapsed, 3),
                            "error_type": error.get("type"),
                            "run_file": run_path.name,
                        }
                    )
                    + "\n"
                )

            attempts.setdefault((puzzle_id, repetition), []).append(
                {
                    "attempt": attempt,
                    "status": status,
                    "won": outcome.get("won"),
                    "file": run_path.name,
                }
            )

            runs_done += 1

            if status == "completed":
                completed_runs += 1

            write_summary(runs_dir, summary_path)

            print(
                f"[{index}/{len(units)}] puzzle {puzzle_id} rep "
                f"{repetition} attempt {attempt}: {status} "
                f"(won={outcome.get('won')}, "
                f"guesses={outcome.get('guesses_used')}, "
                f"{elapsed:.1f}s)",
                flush=True,
            )

    except KeyboardInterrupt:
        print("\nInterrupted. Resume with:")
        print(
            "  python -m multi_agent_testing.experiment.runner resume "
            f"--experiment-dir {experiment_dir}"
        )
        raise SystemExit(130)

    finally:
        write_summary(runs_dir, summary_path)
        print(f"\nSummary: {summary_path}")
        print(
            f"Attempts executed in this invocation: {runs_done}; "
            f"completed games: {completed_runs}"
        )


def run_start(parser, args) -> None:
    validate_start_args(parser, args)
    lineup = lineup_from_args(parser, args)

    paths = {
        "dataset": args.dataset.resolve(),
        "guess list": args.guess_list.resolve(),
        "manifest": args.manifest.resolve(),
    }

    for label, path in paths.items():
        if not path.is_file():
            parser.error(f"Missing {label}: {path}")

    experiment_dir = args.experiment_dir.resolve()

    if experiment_dir.exists():
        parser.error(
            "Experiment directory already exists; use the resume command."
        )

    config = build_config(args)
    config["settings"]["personas"] = lineup.config()

    experiment_dir.mkdir(parents=True)
    (experiment_dir / "runs").mkdir()

    manifest_copy = experiment_dir / "manifest.csv"
    manifest_copy.write_bytes(paths["manifest"].read_bytes())
    config["manifest_copy"] = manifest_copy.name
    config["manifest_sha256"] = file_hash(manifest_copy)

    (experiment_dir / "experiment_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (experiment_dir / "attempts.jsonl").touch()

    execute_plan(
        experiment_dir,
        config,
        max_runs=args.max_runs,
        max_seconds=args.max_seconds,
        allow_peak=args.allow_peak,
    )


def run_resume(args) -> None:
    experiment_dir = args.experiment_dir.resolve()
    config_path = experiment_dir / "experiment_config.json"

    if not config_path.is_file():
        raise SystemExit(f"No experiment config at {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))

    checks = [
        ("dataset", Path(config["dataset"]), config["dataset_sha256"]),
        (
            "guess list",
            Path(config["guess_list"]),
            config["guess_list_sha256"],
        ),
        (
            "manifest",
            experiment_dir / config["manifest_copy"],
            config["manifest_sha256"],
        ),
    ]

    for label, path, expected in checks:
        if not path.is_file():
            raise SystemExit(f"Missing {label}: {path}")

        if file_hash(path) != expected:
            raise SystemExit(
                f"{label} changed since the experiment was frozen; "
                "start a new experiment instead."
            )

    recorded_source = config.get("source_sha256")
    if recorded_source is not None and source_hash() != recorded_source:
        raise SystemExit(
            "The source code changed since the experiment started "
            "(source_sha256 differs). Check out the recorded code_revision "
            f"({config.get('code_revision')}) or start a new experiment."
        )

    try:
        lineup_from_config(config["settings"].get("personas"))
    except ValueError as error:
        raise SystemExit(f"{error} Start a new experiment instead.") from error

    execute_plan(
        experiment_dir,
        config,
        max_runs=args.max_runs,
        max_seconds=args.max_seconds,
        allow_peak=args.allow_peak,
    )


def add_run_controls(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="Stop after this many executed attempts in this invocation.",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=None,
        help="Stop after this many seconds of work, checked between attempts.",
    )
    parser.add_argument(
        "--allow-peak",
        action="store_true",
        help=(
            "DeepSeek only: keep starting games during peak-price hours "
            "(default: pause until off-peak)."
        ),
    )


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    parser = argparse.ArgumentParser(
        description="Run or resume the frozen Wordle debate plan."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser(
        "start",
        help="Create and run a new experiment directory.",
    )
    start.add_argument("--experiment-dir", type=Path, required=True)
    start.add_argument("--name", default=None)
    start.add_argument("--manifest", type=Path, required=True)
    start.add_argument("--dataset", type=Path, required=True)
    start.add_argument("--guess-list", type=Path, required=True)
    start.add_argument(
        "--backend", choices=["ollama", *PROVIDERS], default="zen"
    )
    start.add_argument("--model", required=True)
    start.add_argument("--base-url", required=True)
    start.add_argument(
        "--protocol",
        choices=["chat", "responses"],
        default="chat",
    )
    start.add_argument("--temperature", type=float, default=None)
    start.add_argument(
        "--thinking",
        choices=THINKING_MODES,
        help="DeepSeek reasoning mode; temperature only applies when disabled.",
    )
    start.add_argument(
        "--max-tokens",
        type=int,
        help="Reply cap per call; a cut-off reply gets the repair re-ask.",
    )
    start.add_argument(
        "--json-mode",
        action="store_true",
        help="Ask the provider for a well-formed JSON object (response_format).",
    )
    start.add_argument("--max-rounds", type=int, default=3)
    start.add_argument("--max-repairs", type=int, default=1)
    start.add_argument("--request-timeout", type=float, default=300.0)
    start.add_argument("--api-retries", type=int, default=1)
    start.add_argument("--repetitions", type=int, default=3)
    start.add_argument("--max-attempts", type=int, default=2)
    start.add_argument(
        "--api-key-env",
        help="Key variable (default: OPENCODE_API_KEY for zen, DEEPSEEK_API_KEY for deepseek).",
    )
    start.add_argument("--limit", type=int)
    add_persona_arguments(start)
    add_run_controls(start)

    resume = subparsers.add_parser(
        "resume",
        help="Continue an interrupted experiment directory.",
    )
    resume.add_argument("--experiment-dir", type=Path, required=True)
    add_run_controls(resume)

    args = parser.parse_args()

    if args.command == "start":
        run_start(parser, args)
    else:
        run_resume(args)


if __name__ == "__main__":
    main()
