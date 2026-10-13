from collections import Counter
from collections.abc import Collection
from dataclasses import asdict, dataclass

from .dataset import WordlePuzzle


def normalize_guess(value: str) -> str:
    word = value.strip().upper()

    if len(word) != 5 or not word.isascii() or not word.isalpha():
        raise ValueError("Guess must contain five ASCII letters.")

    return word


def score_guess(guess: str, answer: str) -> str:
    guess = normalize_guess(guess)
    answer = normalize_guess(answer)

    marks = ["B"] * 5
    remaining = Counter()

    # Reserve exact matches first.
    for index, (guessed, actual) in enumerate(zip(guess, answer)):
        if guessed == actual:
            marks[index] = "G"
        else:
            remaining[actual] += 1

    # Allocate remaining copies to misplaced letters.
    for index, letter in enumerate(guess):
        if marks[index] != "G" and remaining[letter] > 0:
            marks[index] = "Y"
            remaining[letter] -= 1

    return "".join(marks)


@dataclass(frozen=True)
class GuessResult:
    guess: str
    feedback: str


class WordleGame:
    def __init__(
        self,
        puzzle: WordlePuzzle,
        *,
        allowed_guesses: Collection[str] | None = None,
        max_attempts: int = 6,
    ) -> None:
        if type(max_attempts) is not int or not 1 <= max_attempts <= 6:
            raise ValueError("max_attempts must be between 1 and 6.")

        self.puzzle_id = puzzle.puzzle_id
        self._answer = normalize_guess(puzzle.answer)
        self.max_attempts = max_attempts
        self._history: list[GuessResult] = []

        self._allowed = (
            {normalize_guess(word) for word in allowed_guesses}
            if allowed_guesses is not None
            else None
        )

        if self._allowed is not None and self._answer not in self._allowed:
            raise ValueError(
                "The answer must be in the allowed vocabulary."
            )

    @property
    def vocabulary(self) -> frozenset[str] | None:
        """The allowed guesses, or None when any five letters are accepted."""

        return frozenset(self._allowed) if self._allowed is not None else None

    @property
    def won(self) -> bool:
        return bool(
            self._history
            and self._history[-1].feedback == "GGGGG"
        )

    @property
    def done(self) -> bool:
        return self.won or len(self._history) >= self.max_attempts

    def observation(self) -> dict:
        """Return only public game information."""

        return {
            "game": "wordle",
            "word_length": 5,
            "history": [
                asdict(result) for result in self._history
            ],
            "attempts_remaining": (
                self.max_attempts - len(self._history)
            ),
            "done": self.done,
            "won": self.won,
            "guess_policy": (
                "supplied_vocabulary"
                if self._allowed is not None
                else "five_ascii_letters_only"
            ),
        }

    def validate_guess(self, guess: str) -> str:
        if self.done:
            raise ValueError("The game has ended.")

        word = normalize_guess(guess)

        if self._allowed is not None and word not in self._allowed:
            raise ValueError(
                "Guess is outside the allowed vocabulary."
            )

        if any(result.guess == word for result in self._history):
            raise ValueError(
                "This prototype does not allow repeated guesses."
            )

        return word

    def guess(self, guess: str) -> GuessResult:
        word = self.validate_guess(guess)

        result = GuessResult(
            guess=word,
            feedback=score_guess(word, self._answer),
        )

        self._history.append(result)
        return result
