import unittest

import random
from pathlib import Path

from ..games.wordle.candidates import filter_candidates, is_consistent, known_letters
from ..games.wordle.dataset import WordlePuzzle
from ..games.wordle.dataset import load_allowed_guesses
from ..games.wordle.engine import WordleGame, score_guess

GUESSES = Path(__file__).resolve().parents[3] / "src" / "data" / "raw" / "allowed_guesses.txt"


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



def satisfies(word: str, known: dict) -> bool:
    """Whether ``word`` obeys every fact in a ``known_letters`` summary."""

    for index, letter in enumerate(known["pattern"].split()):
        if letter != "_" and word[index] != letter:
            return False
    for item in known["misplaced"]:
        letter = item["letter"]
        if letter not in word or any(word[pos - 1] == letter for pos in item["not_positions"]):
            return False
    if any(letter in word for letter in known["absent"]):
        return False
    return all(word.count(letter) == count for letter, count in known["exact_count"].items())


class KnownLettersTests(unittest.TestCase):
    def test_turn_four_of_the_frame_smoke_game(self):
        history = [
            {"guess": "SLATE", "feedback": "BBGBG"},
            {"guess": "BLIND", "feedback": "BBBBB"},
            {"guess": "COUPE", "feedback": "BBBBG"},
        ]

        self.assertEqual(
            known_letters(history),
            {
                "pattern": "_ _ A _ E",
                "misplaced": [],
                "absent": ["B", "C", "D", "I", "L", "N", "O", "P", "S", "T", "U"],
                "exact_count": {},
            },
        )

    def test_yellow_letters_and_repeated_letters(self):
        # SPEED against ABIDE: E at 3 is yellow, the second E is B, D is yellow.
        history = [{"guess": "SPEED", "feedback": score_guess("SPEED", "ABIDE")}]
        known = known_letters(history)

        self.assertEqual(history[0]["feedback"], "BBYBY")
        self.assertEqual(
            known["misplaced"],
            [{"letter": "D", "not_positions": [5]}, {"letter": "E", "not_positions": [3, 4]}],
        )
        self.assertEqual(known["absent"], ["P", "S"])  # E is not absent: one copy exists
        self.assertEqual(known["exact_count"], {"E": 1})

    def test_empty_history(self):
        self.assertEqual(
            known_letters([]),
            {"pattern": "_ _ _ _ _", "misplaced": [], "absent": [], "exact_count": {}},
        )

    @unittest.skipUnless(GUESSES.exists(), "guess list not present")
    def test_every_possible_answer_satisfies_the_summary(self):
        # Soundness on random games: the summary never rules out a word that
        # the feedback still allows, so it cannot mislead the agents.
        words = sorted(load_allowed_guesses(GUESSES))
        rng = random.Random(20261013)

        for _ in range(200):
            answer = rng.choice(words)
            history = [
                {"guess": guess, "feedback": score_guess(guess, answer)}
                for guess in rng.sample(words, rng.randint(1, 5))
            ]
            known = known_letters(history)
            sample = rng.sample(words, 300) + [answer]

            for word in sample:
                if is_consistent(word, history):
                    self.assertTrue(satisfies(word, known), (word, history, known))


if __name__ == "__main__":
    unittest.main()
