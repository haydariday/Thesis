import unittest

from ..games.wordle.candidates import filter_candidates, is_consistent
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



class CandidateTests(unittest.TestCase):
    # RAISE against CIGAR scores YYYBB. VIRAL scores the same, so it stays a
    # candidate; CRANE and SLATE do not.
    HISTORY = [{"guess": "RAISE", "feedback": "YYYBB"}]

    def test_consistent_words_survive(self):
        words = {"CIGAR", "CRANE", "RAISE", "SLATE", "VIRAL"}

        self.assertEqual(filter_candidates(words, []), words)
        self.assertEqual(filter_candidates(words, self.HISTORY), {"CIGAR", "VIRAL"})

    def test_guessed_word_is_not_a_candidate_unless_it_won(self):
        self.assertFalse(is_consistent("RAISE", self.HISTORY))
        self.assertTrue(is_consistent("CIGAR", [{"guess": "CIGAR", "feedback": "GGGGG"}]))

    def test_vocabulary_is_public_and_read_only(self):
        game = WordleGame(WordlePuzzle("test", "CIGAR"), allowed_guesses=["cigar", "APPLE"])

        self.assertEqual(game.vocabulary, frozenset({"CIGAR", "APPLE"}))
        self.assertIsNone(WordleGame(WordlePuzzle("test", "CIGAR")).vocabulary)


if __name__ == "__main__":
    unittest.main()
