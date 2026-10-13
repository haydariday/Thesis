import json
import tempfile
import unittest
from pathlib import Path

from ..experiment.persona_stats import load_games, opener_rows, persona_statistics


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

    def tearDown(self):
        self.tmp.cleanup()

    def test_rates(self):
        games = load_games(self.runs)
        stats = persona_statistics(games, seed=1, resamples=200)

        self.assertEqual(stats["games"], 2)  # the failed run is left out
        self.assertEqual(stats["turns"], 4)
        self.assertEqual(stats["gm_retention_rate"], 0.5)
        self.assertEqual(stats["final_non_candidate_share"], 0.5)
        bold, cautious = stats["advisors"]["bold"], stats["advisors"]["cautious"]
        self.assertEqual((bold["adopted"], cautious["adopted"]), (1, 1))
        self.assertEqual(bold["agreed"], 2)  # SLATE in game 1, GRAPE in game 2
        self.assertEqual((bold["non_candidate"], bold["suggestions_after_turn_1"]), (0, 2))
        self.assertEqual((cautious["non_candidate"], cautious["suggestions_after_turn_1"]), (2, 2))
        check = stats["manipulation_check"]
        self.assertEqual(check["point"], 1.0)
        self.assertLessEqual(check["ci_low"], check["point"])

    def test_openers(self):
        rows = opener_rows("deep", load_games(self.runs))

        turn_one = [(r["word"], r["source"], r["count"]) for r in rows if r["turn"] == 1]
        self.assertEqual(turn_one, [("CRANE", "bold", 1), ("SLATE", "gm", 1)])
        self.assertTrue(all(r["puzzle_id"] == "all" for r in rows if r["turn"] == 1))
        self.assertEqual({r["puzzle_id"] for r in rows if r["turn"] == 2}, {"5"})


if __name__ == "__main__":
    unittest.main()
