import csv
import json
import tempfile
import unittest
from pathlib import Path

from ..experiment import analysis
from ..experiment.summary import SUMMARY_FIELDS


MANIFEST_COLUMNS = (
    "puzzle_id",
    "date",
    "answer",
    "human_mean_score",
    "human_mean_low",
    "human_mean_high",
    "human_loss_pct",
    "human_label",
    "human_mode",
    "human_sample_size_if_known",
    "split",
    "eligibility_notes",
    "selection_seed",
)


def _write_rows(path: Path, fieldnames, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _attempt_row(
    puzzle_id,
    repetition,
    status,
    won,
    score,
    turns,
    gm_stop_turns,
    max_rounds_turns,
):
    row: dict[str, object] = {field: "" for field in SUMMARY_FIELDS}
    row.update(
        {
            "run_id": f"{puzzle_id}-{repetition}-1",
            "run_file": (
                f"puzzle-{puzzle_id}-rep{repetition}-attempt1.json"
            ),
            "puzzle_id": puzzle_id,
            "repetition": repetition,
            "attempt": 1,
            "status": status,
            "won": won,
            "guesses_used": 3,
            "penalized_score": score,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "elapsed_seconds": 120.0,
            "agent_calls": turns,
            "rejected_responses": 0,
            "backend_errors": 0,
            "turns": turns,
            "gm_stop_turns": gm_stop_turns,
            "max_rounds_turns": max_rounds_turns,
        }
    )
    return row


def _manifest_row(
    puzzle_id: str,
    answer: str,
    human_mean: float,
    human_label: str,
):
    return {
        "puzzle_id": puzzle_id,
        "date": "01/01",
        "answer": answer,
        "human_mean_score": human_mean,
        "human_mean_low": human_mean - 0.1,
        "human_mean_high": human_mean + 0.1,
        "human_loss_pct": 3.0,
        "human_label": human_label,
        "human_mode": "standard",
        "human_sample_size_if_known": 1000,
        "split": "pilot",
        "eligibility_notes": "",
        "selection_seed": 20261008,
    }


def _checkpoint(puzzle_id: str, turns: list[dict]) -> dict:
    return {
        "status": "completed",
        "metadata": {"puzzle_id": puzzle_id},
        "turns": turns,
    }


def _turn(termination: str, debate_rounds: int) -> dict:
    return {
        "termination": termination,
        "debate_rounds": debate_rounds,
    }


class TerminationAnalysisTests(unittest.TestCase):
    def build_fixture(self, root: Path, with_runs: bool) -> Path:
        _write_rows(
            root / "manifest.csv",
            MANIFEST_COLUMNS,
            [
                _manifest_row("10", "FRAME", 3.5, "easy"),
                _manifest_row("20", "NYMPH", 4.3, "hard"),
                _manifest_row("30", "ROBOT", 4.5, "hard"),
            ],
        )

        # Primary panel: puzzles 10 and 20 (two completed runs each).
        # Puzzle 30 has one completed run and must stay out of the panel.
        _write_rows(
            root / "run_summary.csv",
            SUMMARY_FIELDS,
            [
                _attempt_row("10", 1, "completed", "True", 3, 3, 3, 0),
                _attempt_row("10", 2, "completed", "True", 4, 2, 1, 1),
                _attempt_row("20", 1, "completed", "True", 5, 4, 2, 2),
                _attempt_row("20", 2, "completed", "False", 7, 3, 3, 0),
                _attempt_row("30", 1, "completed", "True", 3, 2, 2, 0),
            ],
        )

        (root / "experiment_config.json").write_text(
            json.dumps(
                {
                    "experiment_id": "fixture",
                    "settings": {"repetitions": 2},
                    "primary_threshold": 4.0,
                    "thresholds": [3.8, 4.0, 4.2],
                }
            ),
            encoding="utf-8",
        )

        if with_runs:
            runs_dir = root / "runs"
            runs_dir.mkdir()

            checkpoints = {
                "puzzle-10-rep1-attempt1.json": _checkpoint(
                    "10",
                    [
                        _turn("gm_stop", 1),
                        _turn("gm_stop", 1),
                        _turn("gm_stop", 1),
                    ],
                ),
                "puzzle-10-rep2-attempt1.json": _checkpoint(
                    "10",
                    [
                        _turn("gm_stop", 1),
                        _turn("max_rounds", 3),
                    ],
                ),
                "puzzle-20-rep1-attempt1.json": _checkpoint(
                    "20",
                    [
                        _turn("gm_stop", 2),
                        _turn("max_rounds", 3),
                        _turn("max_rounds", 3),
                        _turn("gm_stop", 3),
                    ],
                ),
                "puzzle-20-rep2-attempt1.json": _checkpoint(
                    "20",
                    [
                        _turn("gm_stop", 1),
                        _turn("gm_stop", 1),
                        _turn("gm_stop", 1),
                    ],
                ),
            }

            for name, checkpoint in checkpoints.items():
                (runs_dir / name).write_text(
                    json.dumps(checkpoint), encoding="utf-8"
                )

        return root

    def test_termination_stats_and_panel(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.build_fixture(Path(directory), with_runs=True)
            exit_code = analysis.main(["--experiment-dir", str(root)])

            metrics = json.loads(
                (root / "metrics.json").read_text(encoding="utf-8")
            )
            puzzle_rows = list(
                csv.DictReader(
                    (root / "puzzle_summary.csv").open(
                        "r", encoding="utf-8", newline=""
                    )
                )
            )
            termination_rows = list(
                csv.DictReader(
                    (root / "termination_stats.csv").open(
                        "r", encoding="utf-8", newline=""
                    )
                )
            )

        self.assertEqual(exit_code, 0)

        panel = metrics["panel"]
        self.assertEqual(panel["complete_puzzles"], 2)
        self.assertEqual(panel["incomplete_puzzle_ids"], ["30"])

        overall = metrics["termination_stats"]["overall"]
        self.assertEqual(overall["turns"], 12)
        self.assertEqual(overall["gm_stop_turns"], 9)
        self.assertEqual(overall["max_rounds_turns"], 3)
        self.assertEqual(overall["gm_stop_share"], 0.75)
        self.assertEqual(overall["max_rounds_share"], 0.25)

        by_human = metrics["termination_stats"]["by_human_label"]
        self.assertEqual(by_human["easy"]["turns"], 5)
        self.assertEqual(by_human["easy"]["gm_stop_turns"], 4)
        self.assertEqual(by_human["easy"]["max_rounds_turns"], 1)
        self.assertEqual(by_human["hard"]["turns"], 7)
        self.assertEqual(by_human["hard"]["gm_stop_turns"], 5)
        self.assertEqual(by_human["hard"]["max_rounds_turns"], 2)

        by_system = metrics["termination_stats"]["by_system_label"]
        self.assertEqual(by_system["easy"]["turns"], 5)
        self.assertEqual(by_system["hard"]["turns"], 7)

        by_round = metrics["termination_stats"][
            "rounds_at_termination"
        ]["by_round"]
        self.assertEqual(by_round["1"].get("gm_stop"), 7)
        self.assertEqual(by_round["1"].get("max_rounds", 0), 0)
        self.assertEqual(by_round["2"].get("gm_stop"), 1)
        self.assertEqual(by_round["3"].get("gm_stop"), 1)
        self.assertEqual(by_round["3"].get("max_rounds"), 3)

        puzzle_30 = next(
            row for row in puzzle_rows if row["puzzle_id"] == "30"
        )
        self.assertEqual(puzzle_30["turns"], "2")
        self.assertEqual(puzzle_30["gm_stop_turns"], "2")

        groups = {row["group"]: row for row in termination_rows}
        self.assertEqual(set(groups), {
            "overall",
            "human_easy",
            "human_hard",
            "system_easy",
            "system_hard",
        })
        self.assertEqual(groups["overall"]["turns"], "12")
        self.assertEqual(groups["human_hard"]["turns"], "7")

    def test_termination_stats_without_checkpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.build_fixture(Path(directory), with_runs=False)
            analysis.main(["--experiment-dir", str(root)])

            metrics = json.loads(
                (root / "metrics.json").read_text(encoding="utf-8")
            )

        stats = metrics["termination_stats"]
        self.assertNotIn("rounds_at_termination", stats)
        self.assertEqual(stats["overall"]["turns"], 12)


if __name__ == "__main__":
    unittest.main()
