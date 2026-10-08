import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WordlePuzzle:
    """Private puzzle input for the game engine."""

    puzzle_id: str
    answer: str


def load_puzzle(path: Path, puzzle_id: str) -> WordlePuzzle:
    """Load a puzzle by its explicit JSON key, not its position."""

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise TypeError("Expected a JSON object keyed by puzzle ID.")

    if not puzzle_id.isascii() or not puzzle_id.isdecimal():
        raise ValueError("Puzzle ID must be a numeric string.")

    if puzzle_id not in data:
        raise ValueError(f"Puzzle ID {puzzle_id!r} is absent.")

    record = data[puzzle_id]

    if not isinstance(record, dict):
        raise TypeError("Puzzle record must be a JSON object.")

    number = record.get("num")

    if type(number) is not int or number != int(puzzle_id):
        raise ValueError(
            f"Puzzle {puzzle_id}: num={number!r} does not match its key. "
            "Inspect the source record before using this puzzle."
        )

    answer = record.get("answer")

    if (
        not isinstance(answer, str)
        or re.fullmatch(r"[A-Z]{5}", answer) is None
    ):
        raise ValueError(
            f"Puzzle {puzzle_id} has an invalid answer."
        )

    return WordlePuzzle(
        puzzle_id=puzzle_id,
        answer=answer,
    )
def load_allowed_guesses(path: Path) -> set[str]:
    """Load and validate a one-word-per-line vocabulary."""

    words: set[str] = set()

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            original = line.strip()

            if not original:
                continue

            word = original.upper()

            if (
                not original.isascii()
                or re.fullmatch(r"[A-Z]{5}", word) is None
            ):
                raise ValueError(
                    f"Invalid vocabulary entry at line {line_number}."
                )

            words.add(word)

    if not words:
        raise ValueError("Allowed-guess vocabulary is empty.")

    return words
