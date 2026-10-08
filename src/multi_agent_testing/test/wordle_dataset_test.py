import argparse
from pathlib import Path

from ..games.wordle.dataset import (
    load_allowed_guesses,
    load_puzzle,
)
from ..games.wordle.engine import WordleGame


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to the raw puzzle JSON.",
    )

    parser.add_argument(
        "--puzzle-id",
        required=True,
        help="Exact JSON key identifying the puzzle.",
    )

    parser.add_argument(
        "--guess-list",
        type=Path,
        required=True,
        help="Path to the allowed Wordle guesses, one word per line.",
    )

    args = parser.parse_args()

    puzzle = load_puzzle(
        path=args.dataset,
        puzzle_id=args.puzzle_id,
    )

    allowed_guesses = load_allowed_guesses(args.guess_list)

    game = WordleGame(
        puzzle,
        allowed_guesses=allowed_guesses,
    )

    print(f"Allowed guesses loaded: {len(allowed_guesses)}")
    print(f"Guess policy: {game.observation()['guess_policy']}")
    print("Puzzle loaded successfully")
    print(f"Puzzle ID: {puzzle.puzzle_id}")
    print(f"Answer: {puzzle.answer}")
    print("Engine-side diagnostic only; do not send the answer to agents.")


if __name__ == "__main__":
    main()
