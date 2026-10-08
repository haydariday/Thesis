import unittest

from ..games.wordle.dataset import WordlePuzzle
from ..games.wordle.engine import WordleGame, score_guess


class WordleEngineTests(unittest.TestCase):
    def test_repeated_letters(self):
        self.assertEqual(
            score_guess("ALLEE", "APPLE"),
            "GYBBG",
        )
        self.assertEqual(
            score_guess("EERIE", "SERVE"),
            "BGGBG",
        )

    def test_win(self):
        game = WordleGame(WordlePuzzle("test", "CIGAR"))

        result = game.guess("cigar")

        self.assertEqual(result.guess, "CIGAR")
        self.assertEqual(result.feedback, "GGGGG")
        self.assertTrue(game.won)
        self.assertTrue(game.done)

    def test_loss(self):
        game = WordleGame(
            WordlePuzzle("test", "CIGAR"),
            max_attempts=1,
        )

        game.guess("APPLE")

        self.assertTrue(game.done)
        self.assertFalse(game.won)

    def test_public_observation(self):
        game = WordleGame(WordlePuzzle("test", "CIGAR"))
        observation = game.observation()

        self.assertNotIn("answer", observation)
        self.assertNotIn("puzzle_id", observation)
        self.assertEqual(observation["attempts_remaining"], 6)

    def test_dictionary_validation(self):
        game = WordleGame(
            WordlePuzzle("test", "CIGAR"),
            allowed_guesses=["CIGAR", "APPLE"],
        )

        with self.assertRaises(ValueError):
            game.guess("CRANE")

        self.assertEqual(
            game.observation()["attempts_remaining"],
            6,
        )


if __name__ == "__main__":
    unittest.main()
