import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    load_dotenv(
        Path(__file__).resolve().parent / ".env",
        override=False,
    )

    parser = argparse.ArgumentParser()

    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--guess-list", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)

    parser.add_argument(
        "--backend",
        choices=["ollama", "zen"],
        required=True,
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--temperature", type=float, required=True)
    parser.add_argument("--max-rounds", type=int, default=3)

    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--api-key-env",
        default="OPENCODE_API_KEY",
    )

    args = parser.parse_args()

    if not 1 <= args.max_rounds <= 10:
        parser.error("--max-rounds must be between 1 and 10.")

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive.")

    if (
        args.backend == "zen"
        and not os.environ.get(args.api_key_env, "").strip()
    ):
        parser.error(
            f"Set {args.api_key_env} in .env before starting a batch."
        )

    dataset_path = args.dataset.resolve()
    guess_list_path = args.guess_list.resolve()

    with dataset_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    if not isinstance(raw, dict):
        parser.error("Dataset must be an object keyed by puzzle ID.")

    if any(
        not key.isascii() or not key.isdecimal()
        for key in raw
    ):
        parser.error("Dataset contains a nonnumeric puzzle key.")

    puzzle_ids = sorted(raw, key=int)

    if args.limit is not None:
        puzzle_ids = puzzle_ids[:args.limit]

    output_dir = args.output_dir.resolve()

    if output_dir.exists():
        parser.error(
            "Choose a new output directory to avoid overwriting a run."
        )

    output_dir.mkdir(parents=True)

    config = {
        "settings": vars(args),
        "dataset_sha256": file_hash(dataset_path),
        "guess_list_sha256": file_hash(guess_list_path),
        "selected_puzzle_ids": puzzle_ids,
    }

    with (output_dir / "config.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(config, file, indent=2, default=str)

    consecutive_errors = 0

    with (output_dir / "summary.jsonl").open(
        "w", encoding="utf-8"
    ) as summary:
        for position, puzzle_id in enumerate(puzzle_ids, start=1):
            log_path = output_dir / f"puzzle-{puzzle_id}.log"

            command = [
                sys.executable,
                "-m",
                "multi_agent_testing.test.debate_test",
                "--play",
                "--backend", args.backend,
                "--model", args.model,
                "--base-url", args.base_url,
                "--temperature", str(args.temperature),
                "--max-rounds", str(args.max_rounds),
                "--api-key-env", args.api_key_env,
                "--dataset", str(dataset_path),
                "--puzzle-id", puzzle_id,
                "--guess-list", str(guess_list_path),
            ]

            print(
                f"[{position}/{len(puzzle_ids)}] "
                f"Running puzzle {puzzle_id}",
                flush=True,
            )

            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.run(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                )

            completed = process.returncode == 0

            record = {
                "puzzle_id": puzzle_id,
                "status": (
                    "runner_completed" if completed else "error"
                ),
                "exit_code": process.returncode,
                "log_file": log_path.name,
            }

            summary.write(json.dumps(record) + "\n")
            summary.flush()

            print(
                f"  {record['status']} → {log_path.name}",
                flush=True,
            )

            consecutive_errors = (
                0 if completed else consecutive_errors + 1
            )

            if consecutive_errors >= 3:
                print(
                    "Stopped after three consecutive errors. "
                    "Inspect the logs before continuing."
                )
                raise SystemExit(1)

    print(f"\nBatch finished. Results directory: {output_dir}")


if __name__ == "__main__":
    main()
