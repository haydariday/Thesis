import json

from .engine import GuessResult, WordleGame


class WordleBridge:
    """Expose public state and validate/execute actions."""

    def __init__(self, game: WordleGame) -> None:
        self._game = game

    def observe(self) -> str:
        return json.dumps(
            {
                "rules": (
                    "Guess the hidden five-letter word. "
                    "G means the letter and position are correct. "
                    "Y means an unmatched copy exists elsewhere. "
                    "B means no unmatched copy remains. "
                    "Exact matches are allocated before misplaced letters. "
                    "Use an uppercase word from the allowed vocabulary. "
                    "Repeated guesses are not permitted in this prototype. "
                    "Use only the public history; do not invent feedback."
                    "The action field must contain only the five uppercase "
                    "ASCII letters, with no instruction, spaces, or punctuation. "
                ),
                "observation": self._game.observation(),
            },
            ensure_ascii=False,
        )

    def validate_action(self, action: str) -> str:
        return self._game.validate_guess(action)

    def execute(self, action: str) -> GuessResult:
        return self._game.guess(action)
