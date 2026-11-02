import json
import tempfile
import unittest
from pathlib import Path

from ..experiment.persona_stats import (
    Game,
    advisor_difference,
    herding_counts,
    load_games,
    opener_rows,
    persona_statistics,
)


def suggestion(advisor: str, action: str, gm: str, candidate: bool) -> dict:
    return {
        "round": 1,
        "advisor": advisor,
        "action": action,
        "gm_proposal": gm,
        "agreed": action == gm,
        "is_candidate": candidate,
    }


def turn(gm: str, final: str, adopted: list, bold: tuple, cautious: tuple, final_candidate=True) -> dict:
    return {
        "initial_proposal": gm,
        "final_action": final,
        "gm_retained": gm == final,
        "adopted_from": adopted,
        "advisor_agreed": {"bold": bold[0] == gm, "cautious": cautious[0] == gm},
        "advisor_suggestions": [
            suggestion("bold", bold[0], gm, bold[1]),
            suggestion("cautious", cautious[0], gm, cautious[1]),
        ],
        "is_candidate": {"initial_proposal": True, "final_action": final_candidate},
        "termination": "gm_stop",
        "debate_rounds": 1,
    }


def write_run(directory: Path, name: str, puzzle: str, repetition: int, turns: list, status="completed"):
    run = {
        "status": status,
        "metadata": {
            "puzzle_id": puzzle,
            "repetition": repetition,
            "personas": {"advisors": ["bold", "cautious"]},
        },
        "turns": turns,
    }
    (directory / f"{name}.json").write_text(json.dumps(run), encoding="utf-8")


class PersonaStatsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runs = Path(self.tmp.name)
        # Game 1: GM keeps SLATE, then adopts Cautious's word.
        write_run(self.runs, "a", "5", 1, [
            turn("SLATE", "SLATE", [], ("SLATE", True), ("CRANE", True)),
            turn("BRAKE", "MOUND", ["cautious"], ("GRAPE", True), ("MOUND", False), final_candidate=False),
        ])
        # Game 2: GM adopts Bold's opener, then keeps its word.
        write_run(self.runs, "b", "5", 2, [
            turn("SLATE", "CRANE", ["bold"], ("CRANE", True), ("AUDIO", True)),
            turn("GRAPE", "GRAPE", [], ("GRAPE", True), ("CHOMP", False)),
        ])
        write_run(self.runs, "c", "5", 3, [turn("SLATE", "SLATE", [], ("X", True), ("Y", True))], status="failed")
        # Game 3: Cautious abstains on turn 2; that is neither a candidate nor a non-candidate.
        abstaining = turn("BRAKE", "BRAKE", [], ("GRAPE", True), ("NONE", True))
        abstaining["advisor_suggestions"][1].update(action=None, abstained=True, is_candidate=None, agreed=None)
        abstaining["advisor_agreed"]["cautious"] = None
        write_run(self.runs, "d", "6", 1, [turn("SLATE", "SLATE", [], ("SLATE", True), ("CRANE", True)), abstaining])

    def tearDown(self):
        self.tmp.cleanup()

    def test_rates(self):
        games = load_games(self.runs)
        stats = persona_statistics(games, seed=1, resamples=200)

        self.assertEqual(stats["games"], 3)  # the failed run is left out
        self.assertEqual(stats["turns"], 6)
        self.assertEqual(stats["gm_retention_rate"], 4 / 6)
        bold, cautious = stats["advisors"]["bold"], stats["advisors"]["cautious"]
        self.assertEqual((bold["adopted"], cautious["adopted"]), (1, 1))
        self.assertEqual(bold["agreed"], 3)  # SLATE in games 1 and 3, GRAPE in game 2
        self.assertEqual((bold["non_candidate"], bold["suggestions_after_turn_1"]), (0, 3))
        self.assertEqual((cautious["non_candidate"], cautious["suggestions_after_turn_1"]), (2, 2))
        self.assertEqual((cautious["abstained"], bold["abstained"]), (1, 0))
        check = stats["manipulation_check"]
        self.assertEqual(check["point"], 1.0)
        self.assertLessEqual(check["ci_low"], check["point"])
        test = stats["cautious_vs_bold"]
        # Turn 2 shares: game a 1 vs 0, game b 1 vs 0; game d has no Cautious share.
        self.assertEqual((test["pairs"], test["n"], test["mean_difference"]), (2, 2, 1.0))
        self.assertEqual(test["w_plus"], 3.0)
        self.assertEqual(stats["advisor_difference"]["n"], 2)
        self.assertFalse(stats["solo"])

    def test_openers(self):
        rows = opener_rows("deep", load_games(self.runs))

        turn_one = [(r["word"], r["source"], r["count"]) for r in rows if r["turn"] == 1]
        self.assertEqual(turn_one, [("SLATE", "gm", 2), ("CRANE", "bold", 1)])
        self.assertTrue(all(r["puzzle_id"] == "all" for r in rows if r["turn"] == 1))
        self.assertEqual({r["puzzle_id"] for r in rows if r["turn"] == 2}, {"5", "6"})


def neutral_turn(shares: dict[str, bool]) -> dict:
    return {
        "initial_proposal": "SLATE",
        "final_action": "SLATE",
        "gm_retained": True,
        "adopted_from": [],
        "advisor_agreed": {key: False for key in shares},
        "advisor_suggestions": [
            suggestion(key, "CRANE", "SLATE", candidate) for key, candidate in shares.items()
        ],
        "is_candidate": {"initial_proposal": True, "final_action": True},
        "termination": "gm_stop",
        "debate_rounds": 1,
    }


class AdvisorDifferenceTest(unittest.TestCase):
    KEYS = ("neutral_1", "neutral_2", "neutral_3")

    def games(self) -> list[Game]:
        # neutral_2 is never a candidate after turn 1, neutral_3 half the time.
        opening = neutral_turn({key: True for key in self.KEYS})
        return [
            Game(str(i), 1, self.KEYS, (
                opening,
                neutral_turn({"neutral_1": True, "neutral_2": False, "neutral_3": i % 2 == 0}),
            ))
            for i in range(4)
        ]

    def test_friedman_on_per_game_shares(self):
        result = advisor_difference(self.games(), self.KEYS)
        assert result is not None
        self.assertEqual(result["n"], 4)
        self.assertEqual(result["df"], 2)
        self.assertEqual(result["mean_shares"], {"neutral_1": 0.0, "neutral_2": 1.0, "neutral_3": 0.5})
        self.assertEqual(result["mean_ranks"], {"neutral_1": 1.25, "neutral_2": 2.75, "neutral_3": 2.0})
        # Q = 6.0 after the tie correction (two of the four games tie two advisors).
        self.assertAlmostEqual(result["statistic"], 6.0)
        self.assertAlmostEqual(result["p_value"], 0.049787068, places=6)

    def test_identical_advisors_do_not_differ(self):
        games = [Game(str(i), 1, self.KEYS, (neutral_turn({k: True for k in self.KEYS}),) * 2)
                 for i in range(3)]
        result = advisor_difference(games, self.KEYS)
        assert result is not None
        self.assertEqual((result["statistic"], result["p_value"]), (0.0, 1.0))

    def test_needs_two_advisors(self):
        self.assertIsNone(advisor_difference(self.games(), ("neutral_1",)))

    def test_neutral_statistics_have_no_cautious_bold_test(self):
        stats = persona_statistics(self.games(), seed=1, resamples=50)
        self.assertIsNone(stats["manipulation_check"])
        self.assertIsNone(stats["cautious_vs_bold"])
        self.assertEqual(stats["advisor_difference"]["treatments"], list(self.KEYS))


class HerdingTest(unittest.TestCase):
    KEYS = ("neutral_1", "neutral_2", "neutral_3")

    def item(self, key, action, rnd=1, gm="SLATE", abstained=False):
        return {"round": rnd, "advisor": key, "action": None if abstained else action,
                "gm_proposal": gm, "abstained": abstained}

    def test_counts_copies_of_earlier_dissents(self):
        turn = {"advisor_suggestions": [
            # Round 1: neutral_1 dissents (CRANE), neutral_2 copies it, neutral_3 agrees.
            self.item("neutral_1", "CRANE"), self.item("neutral_2", "CRANE"), self.item("neutral_3", "SLATE"),
            # Round 2: neutral_1 agrees, neutral_2 dissents alone, neutral_3 copies neutral_2.
            self.item("neutral_1", "SLATE", 2), self.item("neutral_2", "AUDIO", 2), self.item("neutral_3", "AUDIO", 2),
        ]}
        counts = herding_counts([Game("1", 1, self.KEYS, (turn,))])
        self.assertEqual(counts["neutral_1"], {"dissents": 1, "dissent_copies": 0})
        self.assertEqual(counts["neutral_2"], {"dissents": 2, "dissent_copies": 1})
        self.assertEqual(counts["neutral_3"], {"dissents": 1, "dissent_copies": 1})

    def test_agreement_and_abstention_are_not_dissents(self):
        turn = {"advisor_suggestions": [
            self.item("neutral_1", "SLATE"), self.item("neutral_2", None, abstained=True),
            self.item("neutral_3", "SLATE"),
        ]}
        counts = herding_counts([Game("1", 1, self.KEYS, (turn,))])
        self.assertEqual(counts["neutral_3"], {"dissents": 0, "dissent_copies": 0})
        self.assertNotIn("neutral_2", counts)

    def test_shares_in_persona_statistics(self):
        turn = neutral_turn({k: True for k in self.KEYS})  # all suggest CRANE against SLATE
        stats = persona_statistics([Game("1", 1, self.KEYS, (turn,))], seed=1, resamples=5)
        advisors = stats["advisors"]
        self.assertEqual([advisors[k]["position"] for k in self.KEYS], [1, 2, 3])
        self.assertIsNone(advisors["neutral_1"]["herding_share"])
        self.assertEqual(advisors["neutral_2"]["herding_share"], 1.0)
        self.assertEqual(advisors["neutral_3"]["dissent_copies"], 1)


class SoloStatisticsTest(unittest.TestCase):
    def test_solo_games_report_no_advisor_statistics(self):
        solo_turn = {
            "initial_proposal": "SLATE",
            "final_action": "SLATE",
            "gm_retained": True,
            "adopted_from": [],
            "advisor_agreed": {},
            "advisor_suggestions": [],
            "is_candidate": {"initial_proposal": True, "final_action": True},
            "termination": "single_decision",
            "debate_rounds": 0,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "solo.json"
            path.write_text(json.dumps({
                "status": "completed",
                "metadata": {"puzzle_id": "7", "repetition": 1, "personas": {"advisors": []}},
                "turns": [solo_turn, solo_turn],
            }), encoding="utf-8")
            games = load_games(Path(tmp))
        stats = persona_statistics(games * 2, seed=1, resamples=20)

        self.assertTrue(stats["solo"])
        self.assertEqual(stats["advisors"], {})
        self.assertIsNone(stats["gm_retention_rate"])
        self.assertIsNone(stats["manipulation_check"])
        self.assertIsNone(stats["cautious_vs_bold"])
        self.assertIsNone(stats["advisor_difference"])
        self.assertEqual(stats["termination"], {"single_decision": 4})
        self.assertEqual(stats["mean_debate_rounds"], 0)


if __name__ == "__main__":
    unittest.main()
