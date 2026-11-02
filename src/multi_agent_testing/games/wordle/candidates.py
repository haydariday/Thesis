"""Which words could still be the answer, judged from public feedback only.

These helpers take the public history (``{"guess", "feedback"}`` pairs from
``WordleGame.observation()``) and never the hidden answer.
"""

from collections.abc import Iterable, Mapping, Sequence

from .engine import score_guess


def is_consistent(word: str, history: Sequence[Mapping[str, str]]) -> bool:
    """True if ``word`` as the answer would have produced every feedback seen."""

    return all(
        score_guess(entry["guess"], word) == entry["feedback"]
        for entry in history
    )


def filter_candidates(
    words: Iterable[str],
    history: Sequence[Mapping[str, str]],
) -> set[str]:
    """The subset of ``words`` still consistent with ``history``."""

    return {word for word in words if is_consistent(word, history)}


def known_letters(history: Sequence[Mapping[str, str]]) -> dict:
    """Restate public feedback the way a Wordle keyboard would show it.

    ``pattern`` holds green letters, ``misplaced`` lists letters known to be in
    the word with the 1-based positions they cannot take, ``absent`` lists
    letters never marked G or Y, and ``exact_count`` gives a letter's count
    when one guess marked some copies present and another copy B.
    """

    pattern = ["_"] * 5
    present: set[str] = set()
    yellow: set[str] = set()
    marked_b: set[str] = set()
    not_positions: dict[str, set[int]] = {}
    exact_count: dict[str, int] = {}

    for entry in history:
        marks = list(zip(entry["guess"], entry["feedback"]))
        hits: dict[str, int] = {}

        for index, (letter, mark) in enumerate(marks):
            if mark == "G":
                pattern[index] = letter
            else:
                not_positions.setdefault(letter, set()).add(index + 1)
            if mark == "Y":
                yellow.add(letter)
            if mark in "GY":
                present.add(letter)
                hits[letter] = hits.get(letter, 0) + 1
            else:
                marked_b.add(letter)

        # A B next to a G/Y copy of the same letter caps its count.
        for letter, mark in marks:
            if mark == "B" and letter in hits:
                exact_count[letter] = hits[letter]

    return {
        "pattern": " ".join(pattern),
        "misplaced": [
            {"letter": letter, "not_positions": sorted(not_positions[letter])}
            for letter in sorted(yellow)
        ],
        "absent": sorted(marked_b - present),
        "exact_count": dict(sorted(exact_count.items())),
    }
