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
